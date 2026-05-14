import json
import re
import os
from groq import Groq
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path=dotenv_path, override=True)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def _call_llm(prompt: str) -> str:
    print(f"DEBUG: Calling LLM with prompt length: {len(prompt)}")
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=4000,
        )
        raw_response = response.choices[0].message.content.strip()
        print(f"DEBUG: LLM response length: {len(raw_response)}")
        return raw_response
    except Exception as e:
        print(f"DEBUG: LLM call failed: {str(e)}")
        raise Exception(f"Lỗi gọi AI: {str(e)}")


def _clean_json_string(json_str: str) -> str:
    """
    Clean JSON string by fixing common issues:
    - Unescaped quotes inside string values
    - Newlines in strings
    - Missing commas
    """
    # Replace smart quotes with regular quotes
    json_str = json_str.replace('"', '"').replace('"', '"')
    json_str = json_str.replace(''', "'").replace(''', "'")

    # Remove BOM if present
    json_str = json_str.lstrip('\ufeff')

    return json_str


def _extract_json_objects(text: str) -> list:
    """
    Extract JSON objects from text using multiple strategies
    """
    results = []

    # Strategy 1: Try to find JSON array by finding first [ and matching to last ]
    try:
        # Find the first [ and last ] to get the complete array
        first_bracket = text.find('[')
        last_bracket = text.rfind(']')
        if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
            json_str = text[first_bracket:last_bracket + 1]
            json_str = _clean_json_string(json_str)
            parsed = json.loads(json_str)
            if isinstance(parsed, list):
                return parsed
    except Exception as e:
        print(f"DEBUG: Strategy 1 failed: {e}")

    # Strategy 2: Try to find JSON array using greedy regex
    try:
        # Look for array pattern (greedy match for complete array)
        match = re.search(r'\[[\s\S]*\]', text)
        if match:
            json_str = match.group()
            json_str = _clean_json_string(json_str)
            parsed = json.loads(json_str)
            if isinstance(parsed, list):
                return parsed
    except Exception as e:
        print(f"DEBUG: Strategy 2 failed: {e}")

    # Strategy 3: Try to find individual JSON objects
    try:
        matches = re.findall(r'\{[\s\S]*?\}', text)
        for match in matches:
            try:
                json_str = _clean_json_string(match)
                obj = json.loads(json_str)
                results.append(obj)
            except:
                continue
        if results:
            return results
    except Exception as e:
        print(f"DEBUG: Strategy 3 failed: {e}")

    # Strategy 4: Try to fix common JSON errors
    try:
        # Fix unescaped quotes inside string values (very common issue)
        # Pattern: find quotes that are inside string values and escape them
        text_fixed = text

        # Try to parse the whole text as JSON
        text_fixed = _clean_json_string(text_fixed)
        parsed = json.loads(text_fixed)
        if isinstance(parsed, list):
            return parsed
        elif isinstance(parsed, dict):
            return [parsed]
    except Exception as e:
        print(f"DEBUG: Strategy 4 failed: {e}")

    return results


def _parse_json(raw: str) -> list[dict]:
    """
    Parse JSON response from AI with comprehensive error handling
    """
    print(f"DEBUG: Starting JSON parsing. Raw response: {raw[:300]}...")
    
    if not raw or raw.strip() == "":
        print("DEBUG: Empty response received")
        raise ValueError("Response từ AI trống")
    
    # Check for error indicators
    error_indicators = ["Internal Server Error", "Error", "error", "ERROR", 
                       "Exception", "exception", "500", "502", "503", "504"]
    raw_stripped = raw.strip()
    for err in error_indicators:
        if err.lower() in raw_stripped.lower():
            raise ValueError(f"Lỗi máy chủ AI: {raw_stripped[:100]}")
    
    if len(raw_stripped) < 10:
        raise ValueError(f"Response quá ngắn: {raw_stripped[:100]}")
    
    # Remove markdown
    raw = re.sub(r"```json\s*|```\s*|```", "", raw).strip()
    
    # Try multiple parsing strategies
    results = _extract_json_objects(raw)
    
    if results:
        print(f"DEBUG: Successfully parsed {len(results)} JSON objects")
        return results
    
    # Last resort: manual question extraction
    print("DEBUG: All JSON parsing strategies failed, attempting manual extraction")
    raise ValueError(f"Không thể parse JSON. Response: {raw[:500]}")


def _get_difficulty_guidelines(difficulty: str) -> str:
    """Trả về hướng dẫn chi tiết cho từng mức độ khó"""
    guidelines = {
        "easy": """ĐỘ KHÓ: DỄ (Cơ bản, Nhận biết)
- Câu hỏi chỉ yêu cầu nhớ lại, nhận biết thông tin trực tiếp từ tài liệu
- Đáp án rõ ràng, nằm trực tiếp trong văn bản
- Không cần suy luận""",
        
        "medium": """ĐỘ KHÓ: TRUNG BÌNH (Thông hiểu, Vận dụng)
- Câu hỏi yêu cầu hiểu ý nghĩa, giải thích khái niệm
- Đáp án cần hiểu ngữ cảnh, không nằm trực tiếp word-for-word""",
        
        "hard": """ĐỘ KHÓ: KHÓ (Phân tích, Đánh giá)
- Câu hỏi yêu cầu phân tích, đánh giá, giải quyết vấn đề phức tạp
- Đáp án cần kết nối nhiều khái niệm, suy luận logic"""
    }
    return guidelines.get(difficulty, guidelines["medium"])


def generate_mcq(context: str, num: int, difficulty: str = "medium") -> list[dict]:
    difficulty_guidelines = _get_difficulty_guidelines(difficulty)
    
    print(f"DEBUG: Generating {num} MCQ questions")
    
    # Limit context to ~4500 chars (~1100 tokens) to stay under Groq's 6000 token limit
    if len(context) > 4500:
        context = context[:4500] + "..."
    
    # Simplified prompt to reduce token usage and JSON errors
    prompt = f"""Tạo {num} câu hỏi trắc nghiệm từ tài liệu sau.

{difficulty_guidelines}

Yêu cầu:
- Mỗi câu có 4 đáp án A, B, C, D
- Chỉ 1 đáp án đúng
- Trả về JSON array

Format JSON:
[
  {{
    "question": "Câu hỏi",
    "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
    "answer": "A",
    "explanation": "Giải thích"
  }}
]

Tài liệu:
{context}

Chỉ trả về JSON, không giải thích thêm."""
    
    try:
        raw = _call_llm(prompt)
        print(f"DEBUG: Raw response: {raw[:500]}...")
        results = _parse_json(raw)
        # LLM có thể trả về nhiều câu hỏi hơn yêu cầu, chỉ lấy số lượng cần thiết
        if len(results) > num:
            results = results[:num]
        return results
    except Exception as e:
        print(f"DEBUG: MCQ generation failed: {str(e)}")
        raise Exception(f"Lỗi sinh câu hỏi: {str(e)}")


def generate_essay(context: str, num: int, difficulty: str = "medium") -> list[dict]:
    difficulty_guidelines = _get_difficulty_guidelines(difficulty)
    
    print(f"DEBUG: Generating {num} essay questions")
    
    # Limit context to ~4500 chars (~1100 tokens) to stay under Groq's 6000 token limit
    if len(context) > 4500:
        context = context[:4500] + "..."
    
    prompt = f"""Tạo {num} câu hỏi tự luận từ tài liệu sau.

{difficulty_guidelines}

Yêu cầu:
- Câu hỏi yêu cầu trình bày, phân tích
- Trả về JSON array

Format JSON:
[
  {{
    "question": "Câu hỏi",
    "suggested_answer": "Gợi ý đáp án",
    "key_points": ["Ý 1", "Ý 2"]
  }}
]

Tài liệu:
{context}

Chỉ trả về JSON, không giải thích thêm."""
    
    try:
        raw = _call_llm(prompt)
        results = _parse_json(raw)
        # LLM có thể trả về nhiều câu hỏi hơn yêu cầu, chỉ lấy số lượng cần thiết
        if len(results) > num:
            results = results[:num]
        return results
    except Exception as e:
        print(f"DEBUG: Essay generation failed: {str(e)}")
        raise Exception(f"Lỗi sinh câu hỏi: {str(e)}")
