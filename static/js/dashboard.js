document.addEventListener("DOMContentLoaded", function () {
    const botoesFiltro = document.querySelectorAll(".btn-filtro");
    const campoBusca = document.getElementById("campoBuscaModulo");
    const cardsModulos = document.querySelectorAll(".card-modulo");
    const mensagemVazia = document.getElementById("mensagemNenhumModulo");

    let categoriaAtiva = "todos";

    function filtrarCards() {
        const termoBusca = (campoBusca.value || "").toLowerCase().trim();
        let quantidadeVisivel = 0;

        cardsModulos.forEach(function (card) {
            const categoriaCard = card.dataset.categoria || "";
            const palavrasCard = (card.dataset.palavras || "").toLowerCase();
            const textoCard = card.textContent.toLowerCase();

            const bateCategoria = categoriaAtiva === "todos" || categoriaCard === categoriaAtiva;
            const bateBusca = termoBusca === "" || palavrasCard.includes(termoBusca) || textoCard.includes(termoBusca);

            if (bateCategoria && bateBusca) {
                card.style.display = "flex";
                quantidadeVisivel++;
            } else {
                card.style.display = "none";
            }
        });

        if (mensagemVazia) {
            mensagemVazia.style.display = quantidadeVisivel === 0 ? "block" : "none";
        }
    }

    botoesFiltro.forEach(function (botao) {
        botao.addEventListener("click", function () {
            botoesFiltro.forEach(function (item) {
                item.classList.remove("ativo");
            });
            botao.classList.add("ativo");
            categoriaAtiva = botao.dataset.categoria;
            filtrarCards();
        });
    });

    if (campoBusca) {
        campoBusca.addEventListener("input", filtrarCards);
    }
});