// Limpa automaticamente todos os formulários ao usar o botão Voltar (Tratamento de bfcache)
window.addEventListener('pageshow', function (event) {
    if (event.persisted || (window.performance && window.performance.navigation.type === 2)) {
        document.querySelectorAll('form').forEach(function (form) {
            form.reset();
        });
        document.querySelectorAll('input[type="text"], input[type="number"], select, textarea').forEach(function (input) {
            if (!input.defaultValue) {
                input.value = '';
            }
        });
    }
});