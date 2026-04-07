import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# 1. Cấu hình ban đầu
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
app = FastAPI(title="Lien Quan Strategy API", version="1.0.0")

# CẤU HÌNH CORS: Cực kỳ quan trọng để Next.js gọi được API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Khi thi thật, bạn có thể để ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Định nghĩa Model dữ liệu cho Request
class ChatRequest(BaseModel):
    message: str

# 3. Hàm đọc dữ liệu "Domain-Specific" từ file txt
def load_knowledge():
    try:
        with open("data-character.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Lỗi đọc file: {e}")
        return ""

# 4. API Endpoint chính
@app.post("/api/chat")
async def chat_handler(request: ChatRequest):
    knowledge = load_knowledge()
    
    if not knowledge:
        raise HTTPException(status_code=500, detail="Thiếu dữ liệu kiến thức Liên Quân!")

    # System Prompt giúp AI đóng vai chuyên gia
    system_instruction = f"""
    Bạn là 'Chiến thần Liên Quân', một AI chuyên gia về chiến thuật và kỹ năng tướng.
    Nhiệm vụ: Sử dụng dữ liệu dưới đây để trả lời câu hỏi người dùng. 
    Phong cách: Ngắn gọn, chuyên sâu, đậm chất game thủ.
    
    DỮ LIỆU TƯỚNG:
    {knowledge}
    """

    try:
        model = genai.GenerativeModel("gemini-3-flash-preview")
        # Gửi prompt kèm theo chỉ dẫn chuyên sâu
        response = model.generate_content([system_instruction, request.message])
        return {"reply": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Chạy server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)