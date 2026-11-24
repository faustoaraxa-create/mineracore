/* ==========================================================================
   MINERACORE - INTERFACE DE INFRAESTRUTURA E APOIO DE MINA
   Responsabilidade exclusiva:
- Ler o cenário primário selecionado no comparativo (localStorage)
- Capturar inputs de Patrol, Trator, Pipa e até 3 Máquinas Extras
- Enviar dados com token CSRF para as APIs Python (/api/sugerir_infra, /api/calcular_infra, /api/agente_infra)
- Renderizar resultados, visão consolidada na mesma tela e diagnósticos
   ========================================================================== */
'use strict';

// =========================================================================
// 1. DADOS INICIAIS DO CONTRATO E CONSTANTES DE INTERFACE
// =========================================================================
const PLANO = JSON.parse(document.getElementById('plano-data')?.textContent || '{}');
const NOME_CONTRATO = PLANO.contrato || 'geral';
const MAX_EXTRAS = 3;

let CENARIO_ATIVO = null;
let MODO_CONSOLIDADO_ATIVO = false;

// =========================================================================
// 2. UTILITÁRIOS DE DOM, FORMATAÇÃO E CABEÇALHO CSRF
// =========================================================================
const el = (id) => document.getElementById(id);
const str = (id) => (el(id)?.value || '').trim();
const fmt = (v) => Math.round(Number(v) || 0).toLocaleString('pt-BR');

// Lê o token CSRF da meta tag no <head> para autorizar requisições POST no Flask
function obterHeadersJson() {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content
        || document.querySelector('input[name="csrf_token"]')?.value
        || '';

    return {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
    };
}

// Exibe ou oculta blocos da interface
function alternarVisibilidade(elemento, visivel) {
    if (!elemento) return;
    elemento.classList.toggle('ocultar', !visivel);
    elemento.style.display = visivel ? 'block' : 'none';
}

// =========================================================================
// 3. RECUPERAÇÃO E RENDERIZAÇÃO DO CENÁRIO PRIMÁRIO (CARGA + TRANSPORTE)
// =========================================================================
function recuperarCenarioAtivo() {
    const slugContrato = String(NOME_CONTRATO).replace(/\s+/g, '_');

    try {
        const porContrato = JSON.parse(localStorage.getItem(`mineracore_cenario_escolhido_${slugContrato}`) || 'null');
        if (porContrato && porContrato.inputs) return porContrato;
    } catch { /* ignora erro de parse */ }

    try {
        const ativo = JSON.parse(localStorage.getItem('mineracore_cenario_escolhido_ativo') || 'null');
        if (ativo && ativo.inputs) return ativo;
    } catch { /* ignora erro de parse */ }

    for (let i = 0; i < localStorage.length; i++) {
        const chave = localStorage.key(i);
        if (chave && chave.startsWith('mineracore_cenario_escolhido_')) {
            try {
                const obj = JSON.parse(localStorage.getItem(chave));
                if (obj && obj.inputs) return obj;
            } catch { /* ignora */ }
        }
    }

    for (let j = 0; j < localStorage.length; j++) {
        const chaveCache = localStorage.key(j);
        if (chaveCache && chaveCache.startsWith('mineracore_cenarios_')) {
            try {
                const lista = JSON.parse(localStorage.getItem(chaveCache));
                if (Array.isArray(lista) && lista.length > 0 && lista[0]?.inputs) {
                    return lista[0];
                }
            } catch { /* ignora */ }
        }
    }

    return null;
}

function renderizarBannerFrotaHerdada() {
    CENARIO_ATIVO = recuperarCenarioAtivo();
    const titulo = el('titulo-cenario-herdado');
    const badgePiso = el('badge-piso-herdado');
    const detalhes = el('detalhes-cenario-herdado');
    if (!titulo || !detalhes) return;

    if (!CENARIO_ATIVO) {
        titulo.textContent = '⚠️ Nenhum cenário primário gravado no navegador — simule e grave uma opção em Carga & Transporte.';
        if (badgePiso) badgePiso.textContent = 'Piso: --';
        detalhes.innerHTML = '';
        return;
    }

    const c = CENARIO_ATIVO;
    const dmtIda = c.dmtIdaKm ?? PLANO.dist_ida ?? 0;
    const dmtVolta = c.dmtVoltaKm ?? PLANO.dist_volta ?? dmtIda;
    const totalPrimaria = c.totalMaquinas ?? ((Number(c.qtdEscavadeiras) || 0) + (Number(c.qtdCaminhoes) || 0));

    titulo.textContent = `✅ Cenário Selecionado: ${c.nome || 'Opção'} (${totalPrimaria} máquinas primárias)`;
    if (badgePiso) badgePiso.textContent = `Piso: ${c.nomePiso || '--'}`;

    detalhes.innerHTML = `
        <div class="item-herdado">
            <small>1. Escavadeiras</small>
            <strong>${c.qtdEscavadeiras}x ${c.inputs.modEscav}</strong>
        </div>
        <div class="item-herdado">
            <small>2. Caminhões</small>
            <strong>${c.qtdCaminhoes}x ${c.inputs.modCam} (${c.inputs.cargaCaminhao} t)</strong>
        </div>
        <div class="item-herdado">
            <small>3. Trajeto (Ida / Volta)</small>
            <strong>Ida: ${dmtIda} km | Volta: ${dmtVolta} km</strong>
        </div>
        <div class="item-herdado">
            <small>4. Match Factor</small>
            <strong>MF ${Number(c.matchFactor || 0).toFixed(2)} (${c.passadas || 0} passes)</strong>
        </div>
    `;
}

// =========================================================================
// 4. EQUIPAMENTOS EXTRAS CRIADOS PELO USUÁRIO (ATÉ 3 UNIDADES)
// =========================================================================
function atualizarContadorExtras() {
    const lista = el('lista-extras-infra');
    const contador = el('contador-extras-infra');
    const btnAdd = el('btn-add-extra-infra');
    if (!lista) return;

    const totalCaixas = lista.querySelectorAll('.caixa-extra-infra').length;
    if (contador) contador.textContent = `${totalCaixas} / ${MAX_EXTRAS} adicionados`;
    if (btnAdd) btnAdd.disabled = totalCaixas >= MAX_EXTRAS;
}

function adicionarCaixaExtraInfra() {
    const lista = el('lista-extras-infra');
    if (!lista) return;

    const atual = lista.querySelectorAll('.caixa-extra-infra').length;
    if (atual >= MAX_EXTRAS) return;

    const idx = atual + 1;
    const caixa = document.createElement('div');
    caixa.className = 'caixa-extra-infra';
    caixa.style.marginTop = '12px';
    caixa.style.paddingTop = '12px';
    caixa.style.borderTop = '1px solid rgba(255,255,255,0.08)';

    caixa.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <strong>Máquina Extra ${idx} (até ${MAX_EXTRAS})</strong>
            <button type="button" class="btn-voltar btn-remover-extra no-print" style="padding: 4px 10px; font-size: 12px;">✕ Remover</button>
        </div>
        <div class="subgrid-2">
            <div class="campo-grupo">
                <label>Equipamento / Função (Pá Carregadeira, Rompedor, Perfuratriz...)</label>
                <input type="text" class="extra-nome" placeholder="Ex: Pá Carregadeira Cat 980 / Perfuratriz">
            </div>
            <div class="campo-grupo">
                <label>Quantidade</label>
                <input type="number" class="extra-qtd" step="1" min="1" max="50" value="1">
            </div>
        </div>
    `;

    caixa.querySelector('.btn-remover-extra')?.addEventListener('click', () => {
        caixa.remove();
        atualizarContadorExtras();
    });

    lista.appendChild(caixa);
    atualizarContadorExtras();
}

function lerExtrasInfra() {
    const caixas = document.querySelectorAll('#lista-extras-infra .caixa-extra-infra');
    const extras = [];
    caixas.forEach((caixa, i) => {
        const nome = (caixa.querySelector('.extra-nome')?.value || '').trim() || `Máquina Extra ${i + 1}`;
        const qtd = (caixa.querySelector('.extra-qtd')?.value || '0').trim();
        extras.push({ nome, qtd });
    });
    return extras.slice(0, MAX_EXTRAS);
}

// Coleta os valores brutos dos inputs para envio ao backend Python
function lerInputsInfra() {
    return {
        modelo_patrol: str('modelo_patrol'),
        extensao_pista_km: str('extensao_pista_km'),
        efic_patrol: str('efic_patrol'),
        modelo_trator: str('modelo_trator'),
        frentes_bota_fora: str('frentes_bota_fora'),
        efic_trator: str('efic_trator'),
        modelo_pipa: str('modelo_pipa'),
        capacidade_pipa_l: str('capacidade_pipa_l'),
        ciclo_reabastecimento_min: str('ciclo_reabastecimento_min'),
        extras: lerExtrasInfra()
    };
}

// =========================================================================
// 5. COMUNICAÇÃO COM AS APIS PYTHON (/api/sugerir_infra e /api/calcular_infra)
// =========================================================================
async function sugerirInfraestrutura() {
    CENARIO_ATIVO = recuperarCenarioAtivo() || CENARIO_ATIVO;

    const resp = await fetch('/api/sugerir_infra', {
        method: 'POST',
        headers: obterHeadersJson(),
        body: JSON.stringify({ cenario: CENARIO_ATIVO })
    });
    if (!resp.ok) {
        alert(`Erro ao sugerir infraestrutura (HTTP ${resp.status}).`);
        return;
    }
    const sug = await resp.json();

    if (sug.patrol) {
        if (el('modelo_patrol')) el('modelo_patrol').value = sug.patrol.modelo;
        if (el('extensao_pista_km')) el('extensao_pista_km').value = sug.patrol.extensao_km;
        if (el('efic_patrol')) el('efic_patrol').value = sug.patrol.efic;
    }
    if (sug.trator) {
        if (el('modelo_trator')) el('modelo_trator').value = sug.trator.modelo;
        if (el('frentes_bota_fora')) el('frentes_bota_fora').value = sug.trator.frentes;
        if (el('efic_trator')) el('efic_trator').value = sug.trator.efic;
    }
    if (sug.pipa) {
        if (el('modelo_pipa')) el('modelo_pipa').value = sug.pipa.modelo;
        if (el('capacidade_pipa_l')) el('capacidade_pipa_l').value = sug.pipa.volume;
        if (el('ciclo_reabastecimento_min')) el('ciclo_reabastecimento_min').value = sug.pipa.ciclo;
    }

    await calcularInfraestrutura();
}

async function calcularInfraestrutura() {
    CENARIO_ATIVO = recuperarCenarioAtivo() || CENARIO_ATIVO;

    const resp = await fetch('/api/calcular_infra', {
        method: 'POST',
        headers: obterHeadersJson(),
        body: JSON.stringify({
            inputs: lerInputsInfra(),
            cenario: CENARIO_ATIVO
        })
    });
    if (!resp.ok) {
        alert(`Erro ao calcular infraestrutura (HTTP ${resp.status}).`);
        return;
    }
    const res = await resp.json();

    renderizarResultadoInfra(res);
}

// =========================================================================
// 6. ALTERNÂNCIA DE VISÃO CONSOLIDADA NA PRÓPRIA PÁGINA
// =========================================================================
function alternarModoConsolidado(forcarEstado = null) {
    const secaoConfig = el('secao-config-infra');
    const btnTopo = el('btn-consolidar-tela');
    const btnRodape = el('btn-consolidar-tela-rodape');

    MODO_CONSOLIDADO_ATIVO = typeof forcarEstado === 'boolean' ? forcarEstado : !MODO_CONSOLIDADO_ATIVO;

    alternarVisibilidade(secaoConfig, !MODO_CONSOLIDADO_ATIVO);

    if (btnTopo) {
        btnTopo.textContent = MODO_CONSOLIDADO_ATIVO
            ? '✏️ Voltar e Editar Parâmetros'
            : '📋 Consolidar Tudo na Tela';
    }
    if (btnRodape) {
        btnRodape.textContent = MODO_CONSOLIDADO_ATIVO
            ? '✏️ Voltar e Editar Parâmetros'
            : '📋 Consolidar Planejamento Geral nesta Página';
    }

    if (MODO_CONSOLIDADO_ATIVO) {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

// =========================================================================
// 7. RENDERIZAÇÃO DOS CARDS, CONSOLIDADO E DIAGNÓSTICO NA TELA
// =========================================================================
function renderizarResultadoInfra(res) {
    const extraCards = (res.extras_validas || []).map((item) => `
        <div class="card-stat">
            <div class="title">${item.nome}</div>
            <div class="value">${item.qtd}</div>
            <div class="unit">Apoio adicional</div>
        </div>
    `).join('');

    if (el('cards-resultado-infra')) {
        el('cards-resultado-infra').innerHTML = `
            <div class="card-stat">
                <div class="title">Motoniveladoras (Patrol)</div>
                <div class="value">${res.qtd_patrol}</div>
                <div class="unit">${res.modelo_patrol} • ${res.extensao_km} km</div>
            </div>
            <div class="card-stat">
                <div class="title">Tratores de Esteiras</div>
                <div class="value">${res.qtd_trator}</div>
                <div class="unit">${res.modelo_trator} • ${res.frentes_bota_fora} frente(s)</div>
            </div>
            <div class="card-stat">
                <div class="title">Caminhões-Pipa</div>
                <div class="value">${res.qtd_pipa}</div>
                <div class="unit">${res.modelo_pipa} • ${fmt(res.demanda_agua_hora_l)} L/h</div>
            </div>
            ${extraCards}
        `;
    }

    const escavResumo = CENARIO_ATIVO?.inputs
        ? `${CENARIO_ATIVO.qtdEscavadeiras}x ${CENARIO_ATIVO.inputs.modEscav}`
        : '--';
    const camResumo = CENARIO_ATIVO?.inputs
        ? `${CENARIO_ATIVO.qtdCaminhoes}x ${CENARIO_ATIVO.inputs.modCam} (${CENARIO_ATIVO.inputs.cargaCaminhao} t)`
        : '--';
    const extrasResumo = (res.extras_validas || []).length > 0
        ? res.extras_validas.map((e) => `${e.qtd}x ${e.nome}`).join(' | ')
        : 'Nenhuma máquina extra';

    if (el('painel-consolidado-mina')) {
        el('painel-consolidado-mina').innerHTML = `
            <div class="consolidado-titulo">Consolidação Geral da Operação (Carga + Transporte + Infraestrutura)</div>
            <div class="consolidado-grid">
                <div class="item-herdado">
                    <small>Frota Primária (Carga & Transp.)</small>
                    <strong>${res.qtd_primaria} máquinas</strong>
                </div>
                <div class="item-herdado">
                    <small>Frota de Infraestrutura & Apoio</small>
                    <strong>${res.total_equipamentos_infra} máquinas</strong>
                </div>
                <div class="item-herdado">
                    <small>Efetivo Total da Mina</small>
                    <strong class="destaque-verde">${res.total_equipamentos_mina} equipamentos</strong>
                </div>
            </div>

            <div class="consolidado-grid" style="margin-top: 12px;">
                <div class="item-herdado">
                    <small>Carga (Escavadeiras)</small>
                    <strong>${escavResumo}</strong>
                </div>
                <div class="item-herdado">
                    <small>Transporte (Caminhões)</small>
                    <strong>${camResumo}</strong>
                </div>
                <div class="item-herdado">
                    <small>Infraestrutura Principal</small>
                    <strong>${res.qtd_patrol}x Patrol | ${res.qtd_trator}x Trator | ${res.qtd_pipa}x Pipa</strong>
                </div>
                <div class="item-herdado">
                    <small>Equipamentos Extras de Apoio</small>
                    <strong>${extrasResumo}</strong>
                </div>
            </div>
        `;
    }

    if (el('diagnostico-infra')) {
        el('diagnostico-infra').innerHTML = `
            <div class="diagnostico-box">
                <div class="diagnostico-titulo">Diagnóstico Técnico de Infraestrutura</div>
                <ul class="diagnostico-lista">${(res.alertas || []).map((a) => `<li>${a}</li>`).join('')}</ul>
            </div>
        `;
    }

    alternarVisibilidade(el('bloco-resultado-infra'), true);

    const btnTopo = el('btn-consolidar-tela');
    if (btnTopo) btnTopo.style.display = 'inline-block';
}

// =========================================================================
// 8. INICIALIZAÇÃO E EVENTOS DA PÁGINA
// =========================================================================
document.addEventListener('DOMContentLoaded', () => {
    alternarVisibilidade(el('bloco-resultado-infra'), false);

    renderizarBannerFrotaHerdada();
    atualizarContadorExtras();

    el('btn-add-extra-infra')?.addEventListener('click', adicionarCaixaExtraInfra);
    el('btn-sugerir-infra')?.addEventListener('click', sugerirInfraestrutura);
    el('btn-calcular-infra')?.addEventListener('click', calcularInfraestrutura);
    el('btn-consolidar-tela')?.addEventListener('click', () => alternarModoConsolidado());
    el('btn-consolidar-tela-rodape')?.addEventListener('click', () => alternarModoConsolidado());
    el('btn-fechar-infra')?.addEventListener('click', () => window.close());
    el('btn-imprimir-infra')?.addEventListener('click', () => window.print());
});