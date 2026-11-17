"""تشغيل ZK system كمنظومة سحابية على سيرفر (لينكس أو ويندوز) بخادم إنتاج (waitress) بدل خادم التطوير.

    pip install -r requirements.txt
    python serve.py

الإعدادات من متغيرات البيئة (انظر .env.example و DEPLOY.md): المنفذ، مجلد البيانات، HTTPS، كلمة مرور المدير الأولى.
"""
import os

from config import Config

os.makedirs(os.path.join(Config.BASE_DIR, "database"), exist_ok=True)
os.makedirs(os.path.join(Config.BASE_DIR, "logs"), exist_ok=True)

from app import app, init_db  # noqa: E402


def main():
    init_db()
    from backup_service import start_auto_backup
    start_auto_backup(app, interval_minutes=int(os.getenv("BACKUP_INTERVAL_MINUTES", "60")))

    from waitress import serve
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    print(f"ZK system يعمل على http://{host}:{port}  (البيانات في {Config.BASE_DIR})")
    # عملية واحدة بعدة خيوط: SQLite وقفل محاولات الدخول في الذاكرة يحتاجان عملية واحدة
    # رؤوس البروكسي (https وعنوان الزبون) يعالجها ProxyFix في security.py عند ERP_BEHIND_PROXY=1
    serve(app, host=host, port=port, threads=int(os.getenv("THREADS", "8")), ident="ZK")


if __name__ == "__main__":
    main()
