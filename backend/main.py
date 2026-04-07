import os
import json
import chromadb
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# --- 1. KHỞI TẠO CHROMADB & EMBEDDING MODEL ---
# Model này biến chữ thành dãy số (Vector)
embed_model = SentenceTransformer('all-MiniLM-L6-v2') 

# Khởi tạo DB lưu trữ trên ổ đĩa (để tắt máy không mất dữ liệu)
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="lienquan_knowledge")

# --- 2. HÀM NẠP DỮ LIỆU (CHỈ CHẠY 1 LẦN HOẶC KHI CẬP NHẬT TƯỚNG) ---
def ingest_data():
    with open("data-character.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Reset lại các list để tránh trùng lặp trong bộ nhớ
    documents = []
    ids = []
    metadatas = []

    # KIỂM TRA TRÙNG LẶP TRƯỚC KHI NẠP
    seen_ids = set()

    for hero in data:
        hero_id = str(hero['id'])
        
        # Nếu chẳng may trong JSON vẫn trùng ID, code sẽ tự bỏ qua hoặc báo lỗi ngay
        if hero_id in seen_ids:
            print(f"Cảnh báo: Phát hiện ID trùng trong JSON: {hero_id} ({hero['name']})")
            continue
        seen_ids.add(hero_id)

        content = (
            f"Tướng: {hero['name']}. Vai trò: {hero['role']}. "
            f"Mô tả: {hero['description']}. "
            f"Chiêu 1: {hero['skill1']}. Chiêu 2: {hero['skill2']}. Chiêu cuối: {hero['skill3']}. "
            f"Điểm mạnh: {hero['strengths']}. Khắc chế: {hero['counters']}."
        )
        
        documents.append(content)
        ids.append(hero_id)
        metadatas.append({"name": hero['name']})

    # Xóa dữ liệu cũ trong collection trước khi nạp (Để đảm bảo sạch 100%)
    existing_count = collection.count()
    if existing_count > 0:
        # Lấy tất cả ID hiện có để xóa
        all_ids = collection.get()['ids']
        if all_ids:
            collection.delete(ids=all_ids)
        print(f"Đã dọn dẹp {existing_count} bản ghi cũ.")

    # Tạo vector và nạp vào ChromaDB
    embeddings = embed_model.encode(documents).tolist()
    collection.add( # Dùng .add vì mình đã xóa sạch ở trên rồi
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )
    print(f"Đã nạp thành công {len(ids)} tướng vào Vector DB!")
# Gọi hàm nạp dữ liệu khi khởi động server
ingest_data()

app = FastAPI()
# (Giữ nguyên cấu trúc CORS ở đây...)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Cho phép tất cả các nguồn (hoặc ["http://localhost:5173"])
    allow_credentials=True,
    allow_methods=["*"], # Cho phép tất cả các phương thức (GET, POST, OPTIONS...)
    allow_headers=["*"], # Cho phép tất cả các loại Header
)

class ChatRequest(BaseModel):
    message: str

chat_histories = {}

@app.post("/api/chat")
async def chat_handler(request: ChatRequest):
    try:
        user_query = request.message
        session_id = "default_user" 

        if session_id not in chat_histories:
            chat_histories[session_id] = []

        # 1. KHỞI TẠO MODEL
        model = genai.GenerativeModel("models/gemini-flash-latest")

        # 2. CHUẨN BỊ LỊCH SỬ (Format đúng chuẩn Google)
        history_for_gemini = []
        for msg in chat_histories[session_id][-6:]:
            # Google dùng role 'user' và 'model'
            history_for_gemini.append({"role": msg["role"], "parts": [msg["content"]]})

        # 3. KỸ THUẬT QUAN TRỌNG: LÀM SẠCH CÂU HỎI (Query Refinement)
        if len(history_for_gemini) > 0:
            # Lấy 2 tin nhắn gần nhất từ lịch sử để giữ context
            recent_context = ""
            if len(chat_histories[session_id]) >= 2:
                # Lấy câu hỏi và trả lời cuối cùng
                last_user_msg = chat_histories[session_id][-2]["content"]
                last_model_msg = chat_histories[session_id][-1]["content"][:200]  # Chỉ lấy 200 ký tự
                recent_context = f"""Câu hỏi trước: {last_user_msg}
Trả lời trước: {last_model_msg}..."""
            
            refine_prompt = f"""Bạn là trợ lý để làm sạch câu hỏi. Dựa trên ngữ cảnh dưới đây, hãy viết lại câu hỏi hiện tại thành một câu hỏi độc lập, ĐẦY ĐỦ, bao gồm các thông tin tham chiếu (nếu có "đó", "nó", "họ", hãy thay thế bằng tên cụ thể từ câu trả lời trước).

NGỮCẢNH:
{recent_context}

Câu hỏi hiện tại: {user_query}

CHỈ TRỊNH LẠI PHẦN CÂU HỎI ĐÃ SỬA, KHÔNG CẦN GIẢI THÍCH."""
            
            # Dùng model để lấy câu hỏi sạch
            refine_response = model.generate_content(refine_prompt)
            search_query = refine_response.text.strip()
        else:
            search_query = user_query

        # 4. TRUY VẤN CHROMADB VỚI CÂU HỎI ĐÃ LÀM SẠCH
        query_embedding = embed_model.encode([search_query]).tolist()
        # Tăng n_results lên 5 để tránh bị "ám ảnh" bởi 1 kết quả nhiễu (như Azzen'ka)
        results = collection.query(query_embeddings=query_embedding, n_results=5)
        retrieved_context = "\n".join(results['documents'][0])

        # 5. THIẾT LẬP CHAT VỚI INSTRUCTION NGHIÊM NGẶT
        chat = model.start_chat(history=history_for_gemini)

        final_prompt = f"""Bạn là chuyên gia Liên Quân Mobile. 
        DỮ LIỆU TỪ HỆ THỐNG:
        ---
        {retrieved_context}
        ---
        YÊU CẦU:
        1. Chỉ trả lời dựa trên dữ liệu trên. 
        2. Nếu trong dữ liệu nhắc đến một tướng (như Azzen'ka) chỉ để làm ví dụ về kẻ bị khắc chế, TUYỆT ĐỐI không tập trung vào tướng đó trừ khi được hỏi.
        3. Nếu không có thông tin, hãy nói 'Dữ liệu hiện tại không đề cập đến vấn đề này'.
        
        Câu hỏi hiện tại: {user_query}"""
        
        response = chat.send_message(final_prompt)

        # 6. CẬP NHẬT LỊCH SỬ (Lưu câu hỏi gốc để giữ tự nhiên)
        chat_histories[session_id].append({"role": "user", "content": user_query})
        chat_histories[session_id].append({"role": "model", "content": response.text})

        return {
            "reply": response.text,
            "context_used": results['metadatas'][0]
        }

    except Exception as e:
        print(f"Lỗi: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
if __name__ == "__main__":
    # Chạy trên port 8000 (mặc định của FastAPI)
    uvicorn.run(app, host="127.0.0.1", port=8000)