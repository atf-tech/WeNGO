document.addEventListener("DOMContentLoaded", function () {

    const needToast = document.querySelector("[toast-list]");
    const needChoices = document.querySelector("[data-choices]");
    const needFlatpickr = document.querySelector("[data-provider]");

    function loadScript(src) {
        return new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = src;
            script.async = true;

            script.onload = resolve;
            script.onerror = reject;

            document.body.appendChild(script);
        });
    }

    async function initLibraries() {
        try {

            if (needToast) {
                await loadScript("https://cdn.jsdelivr.net/npm/toastify-js");
            }

            if (needChoices) {
                await loadScript("/static/dashboard/libs/choices.js/public/assets/scripts/choices.min.js");
            }

            if (needFlatpickr) {
                await loadScript("/static/dashboard/libs/flatpickr/flatpickr.min.js");
            }

            console.log("Libraries Loaded Successfully");

        } catch (err) {
            console.error("Library Load Error:", err);
        }
    }

    if (needToast || needChoices || needFlatpickr) {
        initLibraries();
    }

});