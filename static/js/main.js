document.addEventListener("DOMContentLoaded", function () {
    const toggle = document.getElementById("sidebarToggle");
    const sidebar = document.querySelector(".sidebar");
    if (toggle && sidebar) {
        toggle.addEventListener("click", (e) => { e.stopPropagation(); sidebar.classList.toggle("show"); });
        // على التليفون: لمس أي مكان خارج القائمة يقفلها
        document.addEventListener("click", (e) => {
            if (sidebar.classList.contains("show") && !sidebar.contains(e.target)) sidebar.classList.remove("show");
        });
    }

    // رسائل النجاح تختفي تلقائيًا بعد 4 ثوانٍ، أما التحذيرات والأخطاء فتبقى حتى يغلقها المستخدم
    document.querySelectorAll(".alert-success.alert-dismissible, .alert-info.alert-dismissible").forEach((el) => {
        setTimeout(() => {
            if (window.bootstrap && document.body.contains(el)) bootstrap.Alert.getOrCreateInstance(el).close();
        }, 4000);
    });

    // تمرير القائمة الجانبية تلقائيًا إلى الصفحة الحالية (القائمة طويلة)
    const active = sidebar && sidebar.querySelector("a.active");
    if (active) active.scrollIntoView({ block: "center" });
});
