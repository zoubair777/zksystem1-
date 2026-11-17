# ZK system - صورة تشغيل على سيرفر (أي استضافة تدعم Docker)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ERP_DATA_DIR=/data \
    PORT=8000

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# لا نشغّل البرنامج كمستخدم root: لو حصل اختراق لا يملك صلاحيات على السيرفر كله
RUN useradd --create-home --uid 10001 zk && mkdir -p /data && chown -R zk:zk /data
USER zk

# البيانات (قاعدة البيانات، النسخ، السجلات، مفتاح الجلسات) في /data: اربطه بقرص دائم وإلا تضيع عند التحديث
VOLUME ["/data"]
EXPOSE 8000
CMD ["python", "serve.py"]
