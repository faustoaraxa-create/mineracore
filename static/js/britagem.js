document.addEventListener("DOMContentLoaded", function () {
    // 1. Ajusta a largura da barra de progresso sem CSS inline no HTML
    const barraProgresso = document.querySelector(".barra-preenchimento");
    if (barraProgresso) {
        const percentual = Math.min(parseFloat(barraProgresso.dataset.largura) || 0, 100);
        barraProgresso.style.width = percentual + "%";
    }

    // 2. Aplica máscara numérica brasileira (ex: 19200.0 -> 19.200,0) nos resultados
    const elementosNumero = document.querySelectorAll(".numero-formatado");
    elementosNumero.forEach(function (elemento) {
        const valorBruto = parseFloat(elemento.textContent.trim());
        const casasDecimais = parseInt(elemento.dataset.decimais || "1", 10);

        if (!isNaN(valorBruto)) {
            elemento.textContent = valorBruto.toLocaleString("pt-BR", {
                minimumFractionDigits: casasDecimais,
                maximumFractionDigits: casasDecimais,
            });
        }
    });

    // 3. Controla os botões de ajuda (?) que explicam cada indicador ao clicar
    const botoesAjuda = document.querySelectorAll(".btn-ajuda");
    botoesAjuda.forEach(function (botao) {
        botao.addEventListener("click", function (evento) {
            evento.stopPropagation();
            const idAlvo = botao.dataset.ajuda;
            const caixaExplicacao = document.getElementById(idAlvo);

            // Fecha outras caixas abertas antes de abrir a clicada
            document.querySelectorAll(".explicacao-ajuda").forEach(function (caixa) {
                if (caixa.id !== idAlvo) {
                    caixa.classList.remove("visivel");
                }
            });

            if (caixaExplicacao) {
                caixaExplicacao.classList.toggle("visivel");
            }
        });
    });

    // Fecha qualquer explicação aberta se o usuário clicar fora
    document.addEventListener("click", function () {
        document.querySelectorAll(".explicacao-ajuda").forEach(function (caixa) {
            caixa.classList.remove("visivel");
        });
    });
});