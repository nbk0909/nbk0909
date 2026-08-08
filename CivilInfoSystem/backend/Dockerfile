# ==============================================================================
#  نظام المعلومات المدنية الشامل — حاوية الخلفية
# ==============================================================================

FROM python:3.11-slim

# متغيّرات بيئة بايثون
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Baghdad

WORKDIR /app

# اعتماديات النظام المطلوبة لبناء بعض الحزم
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
 && rm -rf /var/lib/apt/lists/*

# تثبيت الاعتماديات في طبقة منفصلة للاستفادة من ذاكرة البناء المؤقتة
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# التشغيل بمستخدم غير جذري
RUN useradd --create-home --shell /bin/bash civil \
 && mkdir -p /app/uploads /app/backups \
 && chown -R civil:civil /app
USER civil

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
