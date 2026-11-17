import os
import sys


def get_app_dir():
    """المجلد الذي توضع فيه البيانات الدائمة (قاعدة البيانات، النسخ الاحتياطية).
    عند التشغيل كملف .exe (مُجمَّع عبر PyInstaller)، نستخدم مجلد الملف
    التنفيذي نفسه بدل المجلد المؤقت الذي يُحذف بعد إغلاق البرنامج، حتى لا
    تُفقد قاعدة البيانات بين مرات التشغيل."""
    # على السيرفر: مجلد البيانات خارج مجلد الكود (يبقى عند تحديث الكود، ويُربط بقرص دائم في Docker)
    if os.getenv("ERP_DATA_DIR"):
        return os.path.abspath(os.getenv("ERP_DATA_DIR"))
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        # ترتيب قديم (ERP.exe وبجانبه database): نبقى عليه حتى لا تختفي البيانات
        if os.path.isfile(os.path.join(exe_dir, "database", "erp.db")):
            return exe_dir
        # ZK system: كل البيانات (قاعدة، نسخ، سجلات) في مجلد واحد بجانب التطبيق،
        # فنقل المنظومة لجهاز آخر = نسخ مجلد التطبيق كما هو
        return os.path.join(exe_dir, DATA_FOLDER_NAME)
    return os.path.abspath(os.path.dirname(__file__))


DATA_FOLDER_NAME = "ZK_data"
APP_NAME = "ZK system"


def get_resource_dir():
    """المجلد الذي توجد فيه الملفات الثابتة المرفقة (templates/static/fonts).
    عند التشغيل كـ .exe بصيغة onefile، تُستخرج هذه الملفات إلى مجلد مؤقت
    يشير إليه PyInstaller عبر sys._MEIPASS."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.abspath(os.path.dirname(__file__))


BASE_DIR = get_app_dir()
RESOURCE_DIR = get_resource_dir()


class Config:
    BASE_DIR = BASE_DIR
    RESOURCE_DIR = RESOURCE_DIR
    # المفتاح الفعلي يضبطه security.init_security (من البيئة أو ملف عشوائي في مجلد البيانات)
    SECRET_KEY = None
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "database", "erp.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CURRENCY = "د.ل"          # الدينار الليبي
    COMPANY_NAME = APP_NAME
    LOW_STOCK_THRESHOLD = 5
