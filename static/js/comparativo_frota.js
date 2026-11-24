/* =========================================================
   SCRIPT EXCLUSIVO - COMPARATIVO TÉCNICO DE FROTA
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {
    // 1. Controle do Modal de Metodologia
    const modal = document.getElementById("modal-metodologia");
    const btnAbrir = document.getElementById("btn-abrir-metodologia");
    const btnFechar = document.getElementById("btn-fechar-metodologia");

    if (btnAbrir && modal) {
        btnAbrir.addEventListener("click", () => modal.classList.add("ativo"));
    }
    if (btnFechar && modal) {
        btnFechar.addEventListener("click", () => modal.classList.remove("ativo"));
    }
    if (modal) {
        modal.addEventListener("click", (e) => {
            if (e.target === modal) modal.classList.remove("ativo");
        });
    }
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && modal && modal.classList.contains("ativo")) {
            modal.classList.remove("ativo");
        }
    });

    // 2. Destaque amarelo automático no cenário vencedor
    const containerComparativo = document.getElementById("container-comparativo-duplo");
    const caixaParecer = document.getElementById("parecer-tecnico-comparativo");

    function aplicarDestaqueVencedor() {
        if (!containerComparativo || !caixaParecer) return;

        const textoParecer = caixaParecer.textContent.toUpperCase();
        const cards = containerComparativo.children;
        if (cards.length < 2) return;

        caixaParecer.classList.add("parecer-amarelo-ativo");

        const venceuCenario2 =
            textoParecer.includes("CENARIO 2") ||
            textoParecer.includes("CENÁRIO 2") ||
            textoParecer.includes("OPÇÃO 2");

        const indiceVencedor = venceuCenario2 ? 1 : 0;
        const cardVencedor = cards[indiceVencedor];

        if (cardVencedor && !cardVencedor.classList.contains("cenario-vencedor-destaque")) {
            cardVencedor.classList.add("cenario-vencedor-destaque");

            const selo = document.createElement("div");
            selo.className = "selo-melhor-cenario";
            selo.textContent = "🏆 Melhor Cenário Recomendado";
            cardVencedor.insertBefore(selo, cardVencedor.firstChild);
        }
    }

    if (containerComparativo) {
        const observer = new MutationObserver(() => {
            aplicarDestaqueVencedor();
        });
        observer.observe(containerComparativo, { childList: true });
    }
});