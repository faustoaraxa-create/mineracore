/* ==========================================================================
   MINERACORE - MOTOR DE DIMENSIONAMENTO DE FROTA E COMPARATIVO DE OPÇÕES
   ========================================================================== */

// =========================================================================
// 1. CONSTANTES DO CONTRATO E PREMISSAS OPERACIONAIS
// =========================================================================
const PLANO = JSON.parse(document.getElementById('plano-data').textContent || '{}');
const DENSIDADE = Number(PLANO.densidade) || 2.0;
const EMPOLAMENTO = Number(PLANO.empolamento) || 1.25;
const DENSIDADE_SOLTA = DENSIDADE / EMPOLAMENTO;
const RITMO_ALVO_TH = Number(PLANO.ritmo_hora) || 0;
const CICLO_TRANSP_MIN = Number(PLANO.tempo_ciclo) || 0;
const DIST_IDA_KM = Number(PLANO.dist_ida) || 0;
const DIST_VOLTA_KM = Number(PLANO.dist_volta) || DIST_IDA_KM;
const HORAS_UTEIS_ANO = Number(PLANO.total_horas_uteis) || 0;

// Chave única de cache vinculada ao nome do contrato atual
const CHAVE_CACHE_CENARIOS = `mineracore_cenarios_${(PLANO.contrato || 'geral').replace(/\s+/g, '_')}`;
let ULTIMA_SIMULACAO = null;

// =========================================================================
// 2. ATUALIZAÇÕES INTERATIVAS DE INTERFACE (PISO E ESCAVADEIRA)
// =========================================================================

function atualizarFatorEnchimentoPiso() {
    const perfilPiso = document.getElementById('perfil_piso').value;
    const inputEnchimento = document.getElementById('fator_enchimento_pct');
    inputEnchimento.value = (perfilPiso === 'rocha') ? 80 : 90;
    atualizarPreviewEscavadeira();
}

function atualizarPreviewEscavadeira() {
    const cacamba = parseFloat(document.getElementById('cacamba_m3').value) || 0;
    const enchimento = (parseFloat(document.getElementById('fator_enchimento_pct').value) || 90) / 100;
    const ciclo = parseFloat(document.getElementById('ciclo_escav_seg').value) || 0;
    const efic = (parseFloat(document.getElementById('efic_escav').value) || 83) / 100;

    const preview = document.getElementById('preview-escavadeira');
    const badge = document.getElementById('badge-classe-escav');

    if (cacamba > 0) {
        const massaPasse = cacamba * enchimento * DENSIDADE_SOLTA;
        const prodUnit = ciclo > 0 ? ((3600 / ciclo) * efic * massaPasse) : 0;

        if (cacamba >= 12) badge.textContent = 'Mineração Pesada (200t+)';
        else if (cacamba >= 6) badge.textContent = 'Mineração Média (90t–140t)';
        else badge.textContent = 'Apoio / Pequeno Porte (35t–50t)';

        preview.innerHTML = `
            <span>Massa/Passe: <strong>${massaPasse.toFixed(2)} t</strong> (${(cacamba * enchimento).toFixed(1)} m³ soltos)</span>
            <span>Prod. Unitária: <strong>${prodUnit > 0 ? prodUnit.toFixed(1) + ' t/h' : '--'}</strong></span>
        `;
    } else {
        badge.textContent = 'Classe Carga';
        preview.innerHTML = `
            <span>Massa/Passe: <strong>-- t</strong></span>
            <span>Prod. Unitária: <strong>-- t/h</strong></span>
        `;
    }
}

// =========================================================================
// 3. MOTOR DE SUGESTÃO DE FROTA POR ESCALA DE PRODUÇÃO
// =========================================================================

function sugerirFrotaCompativel() {
    const perfilPiso = document.getElementById('perfil_piso').value;
    const enchimentoPct = perfilPiso === 'rocha' ? 80 : 90;
    document.getElementById('fator_enchimento_pct').value = enchimentoPct;

    let criterioTexto = '';

    if (RITMO_ALVO_TH >= 5000) {
        document.getElementById('modelo_escavadeira').value = 'Cat 6020B / Komatsu PC2000 (Classe 200t–225t)';
        document.getElementById('cacamba_m3').value = '14.0';
        document.getElementById('ciclo_escav_seg').value = '28';
        document.getElementById('efic_escav').value = '83';

        document.getElementById('modelo_caminhao').value = 'Cat 777 / Komatsu HD785 (Fora-de-Estrada 100t)';
        document.getElementById('carga_caminhao_t').value = '100';
        document.getElementById('efic_transp').value = '85';

        document.getElementById('modelo_patrol').value = 'Cat 16M / 24M (Mineração Pesada)';
        document.getElementById('modelo_trator').value = perfilPiso === 'movedico' ? 'Cat D9 / D10' : 'Cat D8T / D9';
        criterioTexto = 'Alta produção (> 5.000 t/h): Frota pesada acoplada em 5 passes de 14 m³.';
    } else if (RITMO_ALVO_TH >= 2000) {
        document.getElementById('modelo_escavadeira').value = 'Cat 6015B / Komatsu PC1250 (Classe 120t–140t)';
        document.getElementById('cacamba_m3').value = '8.5';
        document.getElementById('ciclo_escav_seg').value = '27';
        document.getElementById('efic_escav').value = '83';

        document.getElementById('modelo_caminhao').value = 'Cat 775 / Komatsu HD605 (Fora-de-Estrada 65t)';
        document.getElementById('carga_caminhao_t').value = '65';
        document.getElementById('efic_transp').value = '85';

        document.getElementById('modelo_patrol').value = 'Cat 16M';
        document.getElementById('modelo_trator').value = 'Cat D8T';
        criterioTexto = 'Produção intermediária (2.000 a 5.000 t/h): Acoplamento em 5 passes de 8,5 m³.';
    } else if (RITMO_ALVO_TH >= 800) {
        document.getElementById('modelo_escavadeira').value = 'Cat 395 / Komatsu PC800 (Classe 90t)';
        document.getElementById('cacamba_m3').value = '6.5';
        document.getElementById('ciclo_escav_seg').value = '26';
        document.getElementById('efic_escav').value = '83';

        document.getElementById('modelo_caminhao').value = 'Cat 773 / Volvo R60 (Fora-de-Estrada 55t)';
        document.getElementById('carga_caminhao_t').value = '55';
        document.getElementById('efic_transp').value = '85';

        document.getElementById('modelo_patrol').value = 'Cat 14M / 16M';
        document.getElementById('modelo_trator').value = 'Cat D8T';
        criterioTexto = 'Média escala (800 a 2.000 t/h): Acoplamento em 5 passes de 6,5 m³.';
    } else {
        document.getElementById('modelo_escavadeira').value = 'Cat 352 / Komatsu PC490 (Classe 50t)';
        document.getElementById('cacamba_m3').value = '4.5';
        document.getElementById('ciclo_escav_seg').value = '24';
        document.getElementById('efic_escav').value = '83';

        document.getElementById('modelo_caminhao').value = 'Scania G500 / Volvo FMX 8x4 (32t)';
        document.getElementById('carga_caminhao_t').value = '32';
        document.getElementById('efic_transp').value = '85';

        document.getElementById('modelo_patrol').value = 'Cat 140 / John Deere 670G';
        document.getElementById('modelo_trator').value = 'Cat D6T';
        criterioTexto = 'Pequena escala (< 800 t/h): Caminhões rodoviários pesados acoplados em 5 passes de 4,5 m³.';
    }

    if (!document.getElementById('extensao_pista_km').value) {
        document.getElementById('extensao_pista_km').value = DIST_IDA_KM;
    }
    if (!document.getElementById('margem_falha').value) {
        document.getElementById('margem_falha').value = '10';
    }

    atualizarPreviewEscavadeira();
    simularFrota(criterioTexto);
}

// =========================================================================
// 4. CÁLCULO PRINCIPAL DE DIMENSIONAMENTO E DIAGNÓSTICO DE ENGENHARIA
// =========================================================================

function simularFrota(criterioSugestao = '') {
    const perfilPiso = document.getElementById('perfil_piso').value;
    const margemFalhaPct = parseFloat(document.getElementById('margem_falha').value) || 0;
    const fatorContingencia = 1 + (margemFalhaPct / 100);

    const modEscav = document.getElementById('modelo_escavadeira').value.trim();
    const cacamba = parseFloat(document.getElementById('cacamba_m3').value) || 0;
    const fatorEnchimento = (parseFloat(document.getElementById('fator_enchimento_pct').value) || 90) / 100;
    const cicloEscav = parseFloat(document.getElementById('ciclo_escav_seg').value) || 0;
    const eficEscavBase = (parseFloat(document.getElementById('efic_escav').value) || 83) / 100;

    const modCam = document.getElementById('modelo_caminhao').value.trim();
    const cargaCaminhao = parseFloat(document.getElementById('carga_caminhao_t').value) || 0;
    const eficTranspBase = (parseFloat(document.getElementById('efic_transp').value) || 85) / 100;

    const modPatrol = document.getElementById('modelo_patrol').value.trim();
    const extensaoPista = parseFloat(document.getElementById('extensao_pista_km').value) || DIST_IDA_KM;
    const modTrator = document.getElementById('modelo_trator').value.trim();

    if (cacamba <= 0 || cicloEscav <= 0 || cargaCaminhao <= 0) {
        alert('Preencha a capacidade da caçamba, o tempo de ciclo da escavadeira e a carga útil do caminhão.');
        return;
    }

    atualizarPreviewEscavadeira();

    let fatorPisoTransp = 1.00;
    let divisorPatrolKm = 4.0;
    let extraTrator = 0;
    let nomePiso = 'Cascalho Compactado / Seco';

    if (perfilPiso === 'argila') {
        fatorPisoTransp = 0.85;
        divisorPatrolKm = 2.5;
        nomePiso = 'Argiloso / Escorregadio';
    } else if (perfilPiso === 'movedico') {
        fatorPisoTransp = 0.78;
        divisorPatrolKm = 2.0;
        extraTrator = 1;
        nomePiso = 'Terreno Movediço / Instável';
    } else if (perfilPiso === 'rocha') {
        nomePiso = 'Rocha Detonada / Abrasivo';
    }

    // 4.1 Dimensionamento de Carga (Escavadeiras)
    const toneladasPorConchada = cacamba * fatorEnchimento * DENSIDADE_SOLTA;
    const ciclosHora = (3600 / cicloEscav) * eficEscavBase;
    const prodEscavadeiraTH = ciclosHora * toneladasPorConchada;
    const escavNominal = Math.ceil(RITMO_ALVO_TH / prodEscavadeiraTH);
    const qtdEscavadeiras = Math.ceil((RITMO_ALVO_TH / prodEscavadeiraTH) * fatorContingencia);

    // 4.2 Dimensionamento de Transporte (Caminhões) e Acoplamento
    const passadas = Math.max(1, Math.round(cargaCaminhao / toneladasPorConchada));
    const cargaReal = passadas * toneladasPorConchada;
    const fatorCarregamentoPct = (cargaReal / cargaCaminhao) * 100;
    const tempoCargaMin = (passadas * cicloEscav) / 60;
    const cicloTotalCaminhao = CICLO_TRANSP_MIN + tempoCargaMin;
    const viagensHoraPorCaminhao = (60 / cicloTotalCaminhao) * (eficTranspBase * fatorPisoTransp);
    const prodPorCaminhaoTH = viagensHoraPorCaminhao * cargaReal;
    const camNominal = Math.ceil(RITMO_ALVO_TH / prodPorCaminhaoTH);
    const qtdCaminhoes = Math.ceil((RITMO_ALVO_TH / prodPorCaminhaoTH) * fatorContingencia);

    const matchFactor = (camNominal * tempoCargaMin) / (escavNominal * cicloTotalCaminhao);
    const caminhoesPorEscavadeira = (qtdCaminhoes / qtdEscavadeiras).toFixed(1);

    const memorialDiv = document.getElementById('memorial-sugestao');
    if (criterioSugestao) {
        memorialDiv.style.display = 'block';
        document.getElementById('memorial-sugestao-grid').innerHTML = `
            <div class="memorial-item">
                <small>Critério de Seleção</small>
                <strong>${criterioSugestao}</strong>
            </div>
            <div class="memorial-item">
                <small>Massa por Passe (${(fatorEnchimento * 100).toFixed(0)}% ench.)</small>
                <strong>${toneladasPorConchada.toFixed(2)} t / conchada</strong>
            </div>
            <div class="memorial-item">
                <small>Carregamento do Caminhão</small>
                <strong>${passadas} passes = ${cargaReal.toFixed(1)} t (${fatorCarregamentoPct.toFixed(0)}%)</strong>
            </div>
            <div class="memorial-item">
                <small>Tempo de Carga + Manobra</small>
                <strong>${tempoCargaMin.toFixed(2)} min / caminhão</strong>
            </div>
        `;
    } else {
        memorialDiv.style.display = 'none';
    }

    // 4.3 Cálculo de Rodagem Total
    const kmPorViagem = DIST_IDA_KM + DIST_VOLTA_KM;
    const viagensTotaisHora = RITMO_ALVO_TH / cargaReal;
    const kmTotalHora = viagensTotaisHora * kmPorViagem;
    const kmTotalAno = kmTotalHora * HORAS_UTEIS_ANO;

    // 4.4 Dimensionamento da Frota Auxiliar
    const qtdPatrol = Math.max(1, Math.ceil(Math.max(extensaoPista / divisorPatrolKm, qtdCaminhoes / 7)));
    const qtdTrator = Math.max(1, qtdEscavadeiras + extraTrator);

    // 4.5 Regras de Diagnóstico e Validação de Engenharia
    const alertas = [];
    if (passadas > 5) {
        alertas.push(`⚠️ <strong>Acoplamento Carga/Transporte (${passadas} passes):</strong> Acima da faixa ideal (3 a 5 conchadas). Risco de fila de caminhões na praça; avalie aumentar a caçamba da escavadeira.`);
    } else if (passadas < 3) {
        alertas.push(`⚠️ <strong>Acoplamento Carga/Transporte (${passadas} passes):</strong> Abaixo de 3 conchadas. Risco de impacto excessivo na báscula e subutilização da escavadeira.`);
    } else {
        alertas.push(`✅ <strong>Acoplamento Carga/Transporte (${passadas} passes):</strong> Dentro da faixa ideal de engenharia (3 a 5 conchadas por caminhão, atingindo ${fatorCarregamentoPct.toFixed(1)}% da carga útil).`);
    }

    if (fatorCarregamentoPct > 110) {
        alertas.push(`🚨 <strong>Sobrecarga na Báscula (${fatorCarregamentoPct.toFixed(0)}% da carga útil):</strong> ${passadas} passes totalizam ${cargaReal.toFixed(1)} t para um caminhão de ${cargaCaminhao} t. Reduza a caçamba ou aumente o porte do caminhão.`);
    }

    if (matchFactor < 0.50) {
        alertas.push(`⚠️ <strong>Escavadeira Superdimensionada (Ociosidade ${((1 - matchFactor) * 100).toFixed(0)}%):</strong> A capacidade da escavadeira (${prodEscavadeiraTH.toFixed(0)} t/h) é muito superior à demanda do transporte (${(qtdCaminhoes * prodPorCaminhaoTH).toFixed(0)} t/h). Utilize uma escavadeira de menor porte.`);
    }

    if (/\b(336|320|323|pc200|pc210|pc240|ec210|ec220)\b/i.test(modEscav) && cacamba > 4.0) {
        alertas.push(`🚨 <strong>Incompatibilidade de Caçamba:</strong> O modelo informado (${modEscav}) é de porte médio e não comporta caçamba de ${cacamba} m³ (classe mineração pesada).`);
    }

    if (cargaCaminhao >= 60 && /\b(140|120|670|rg140)\b/i.test(modPatrol)) {
        alertas.push(`🚨 <strong>Motoniveladora Subdimensionada:</strong> Caminhões de ${cargaCaminhao} t exigem patrol pesada (classe Cat 16M / 24M) para largura de leira e coroamento de pista; a ${modPatrol} é fraca para esse porte.`);
    }

    if (cargaCaminhao >= 60 && /\b(d5|d6|d6t|d61|d65)\b/i.test(modTrator)) {
        alertas.push(`🚨 <strong>Trator Subdimensionado:</strong> Pilhas descarregadas por caminhões de ${cargaCaminhao} t exigem trator pesado (classe Cat D8T / D9) no bota-fora; o ${modTrator} perderá rendimento.`);
    }

    if ((perfilPiso === 'argila' || perfilPiso === 'movedico') && cargaCaminhao >= 60) {
        alertas.push(`⚠️ <strong>Alerta Geotécnico (${nomePiso}):</strong> Operação com fora-de-estrada pesado exige revestimento primário (cascalhamento) e drenagem contínua para evitar atolamento e perda de ciclo.`);
    }

    // 4.6 Renderização dos Resultados na Tela
    document.getElementById('resumo-km-terreno').innerHTML = `
        <strong>Condição Operacional:</strong> ${nomePiso} |
        <strong>Margem de Falha:</strong> +${margemFalhaPct}% |
        <strong>Rodagem Total da Frota:</strong> ${kmTotalHora.toFixed(1)} km/h
        (${kmTotalAno.toLocaleString('pt-BR', { maximumFractionDigits: 0 })} km/ano em ${kmPorViagem.toFixed(1)} km/ciclo)
    `;

    const container = document.getElementById('cards-resultado-frota');
    container.innerHTML = `
        <div class="card-stat">
            <div class="title">Escavadeiras</div>
            <div class="value">${qtdEscavadeiras}</div>
            <div class="unit">Nominal: ${escavNominal} | ${prodEscavadeiraTH.toFixed(1)} t/h (${toneladasPorConchada.toFixed(1)} t/passe)</div>
        </div>
        <div class="card-stat">
            <div class="title">Caminhões</div>
            <div class="value">${qtdCaminhoes}</div>
            <div class="unit">Nominal: ${camNominal} | ${prodPorCaminhaoTH.toFixed(1)} t/h (${passadas} passes)</div>
        </div>
        <div class="card-stat">
            <div class="title">Motoniveladoras</div>
            <div class="value">${qtdPatrol}</div>
            <div class="unit">pista ${extensaoPista} km (${nomePiso.split('/')[0].trim()})</div>
        </div>
        <div class="card-stat">
            <div class="title">Tratores de Esteiras</div>
            <div class="value">${qtdTrator}</div>
            <div class="unit">apoio praça / bota-fora</div>
        </div>
    `;

    let statusMF = 'Equilibrado (0.95 a 1.05)';
    let classeMF = 'mf-ok';
    if (matchFactor < 0.95) {
        statusMF = 'Subdimensionado (< 0.95 — escavadeira aguarda caminhão)';
        classeMF = 'mf-alerta';
    } else if (matchFactor > 1.05) {
        statusMF = 'Saturado (> 1.05 — formação de fila na frente de lavra)';
        classeMF = 'mf-saturado';
    }

    document.getElementById('indicadores-acoplamento').innerHTML = `
        <div class="acoplamento-grid">
            <div>
                <span class="label-indicador">Match Factor (Acoplamento):</span>
                <strong class="valor-indicador ${classeMF}">${matchFactor.toFixed(2)} — ${statusMF}</strong>
            </div>
            <div>
                <span class="label-indicador">Distribuição por Frente de Lavra:</span>
                <strong class="valor-indicador">~${caminhoesPorEscavadeira} caminhões / escavadeira</strong>
            </div>
            <div>
                <span class="label-indicador">Capacidade Instalada Total:</span>
                <strong class="valor-indicador destaque-ritmo">${(qtdEscavadeiras * prodEscavadeiraTH).toFixed(0)} t/h (Carga) | ${(qtdCaminhoes * prodPorCaminhaoTH).toFixed(0)} t/h (Transp.)</strong>
            </div>
        </div>
    `;

    document.getElementById('diagnostico-engenharia').innerHTML = `
        <div class="diagnostico-box">
            <div class="diagnostico-titulo">Diagnóstico Técnico de Engenharia & Compatibilidade</div>
            <ul class="diagnostico-lista">
                ${alertas.map(item => `<li>${item}</li>`).join('')}
            </ul>
        </div>
    `;

    ULTIMA_SIMULACAO = {
        nomePiso,
        qtdEscavadeiras,
        prodEscavadeiraTH,
        qtdCaminhoes,
        prodPorCaminhaoTH,
        qtdPatrol,
        qtdTrator,
        passadas,
        matchFactor,
        kmTotalHora,
        inputs: {
            perfilPiso,
            margemFalhaPct,
            modEscav,
            cacamba,
            fatorEnchimentoPct: fatorEnchimento * 100,
            cicloEscav,
            eficEscavPct: eficEscavBase * 100,
            modCam,
            cargaCaminhao,
            eficTranspPct: eficTranspBase * 100,
            modPatrol,
            extensaoPista,
            modTrator,
            tipoServicoTrator: document.getElementById('tipo_servico_trator').value
        }
    };

    document.getElementById('bloco-resultado-frota').style.display = 'block';
}

// =========================================================================
// 5. GERENCIAMENTO DE CACHE (MÁX. 2 OPÇÕES) E PÁGINA COMPARATIVA EXECUTIVA
// =========================================================================

function obterCenariosCache() {
    try {
        const dados = JSON.parse(localStorage.getItem(CHAVE_CACHE_CENARIOS));
        return Array.isArray(dados) ? dados : [];
    } catch (e) {
        return [];
    }
}

function salvarCenarioCache() {
    if (!ULTIMA_SIMULACAO) {
        alert('Execute uma simulação primeiro clicando em "Simular Frota Ideal" antes de gravar a opção.');
        return;
    }

    const cenarios = obterCenariosCache();
    if (cenarios.length >= 2) {
        alert('Limite de 2 opções atingido para comparação frente a frente. Remova uma opção antes de gravar outra.');
        return;
    }

    const inputNome = document.getElementById('nome_cenario');
    const nomeCenario = (inputNome && inputNome.value.trim()) || `Opção ${cenarios.length + 1}`;

    cenarios.push({
        id: Date.now(),
        nome: nomeCenario,
        ...ULTIMA_SIMULACAO
    });

    localStorage.setItem(CHAVE_CACHE_CENARIOS, JSON.stringify(cenarios));
    if (inputNome) inputNome.value = '';

    renderizarTabelaComparativa();

    const feedback = document.getElementById('feedback-cenario');
    if (feedback) {
        feedback.textContent = `✅ "${nomeCenario}" gravada (${cenarios.length}/2)!`;
        setTimeout(() => { feedback.textContent = ''; }, 3500);
    }
}

function carregarCenarioNoFormulario(id) {
    const cenario = obterCenariosCache().find(c => c.id === id);
    if (!cenario) return;

    document.getElementById('perfil_piso').value = cenario.inputs.perfilPiso;
    document.getElementById('margem_falha').value = cenario.inputs.margemFalhaPct;
    document.getElementById('modelo_escavadeira').value = cenario.inputs.modEscav;
    document.getElementById('cacamba_m3').value = cenario.inputs.cacamba;
    document.getElementById('fator_enchimento_pct').value = cenario.inputs.fatorEnchimentoPct;
    document.getElementById('ciclo_escav_seg').value = cenario.inputs.cicloEscav;
    document.getElementById('efic_escav').value = cenario.inputs.eficEscavPct;

    document.getElementById('modelo_caminhao').value = cenario.inputs.modCam;
    document.getElementById('carga_caminhao_t').value = cenario.inputs.cargaCaminhao;
    document.getElementById('efic_transp').value = cenario.inputs.eficTranspPct;

    document.getElementById('modelo_patrol').value = cenario.inputs.modPatrol;
    document.getElementById('extensao_pista_km').value = cenario.inputs.extensaoPista;
    document.getElementById('modelo_trator').value = cenario.inputs.modTrator;
    document.getElementById('tipo_servico_trator').value = cenario.inputs.tipoServicoTrator;

    simularFrota();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function removerCenarioCache(id) {
    const filtrados = obterCenariosCache().filter(c => c.id !== id);
    localStorage.setItem(CHAVE_CACHE_CENARIOS, JSON.stringify(filtrados));
    renderizarTabelaComparativa();
}

function limparCenariosCache() {
    if (confirm('Deseja apagar as opções gravadas neste contrato?')) {
        localStorage.removeItem(CHAVE_CACHE_CENARIOS);
        renderizarTabelaComparativa();
    }
}

function renderizarTabelaComparativa() {
    const cenarios = obterCenariosCache();
    const bloco = document.getElementById('bloco-comparativo-cenarios');
    const lista = document.getElementById('lista-mini-cenarios');
    const resumo = document.getElementById('resumo-cenarios-gravados');

    if (!bloco || !lista) return;

    if (cenarios.length === 0) {
        bloco.style.display = 'none';
        return;
    }

    bloco.style.display = 'block';
    if (resumo) {
        resumo.textContent = `${cenarios.length} de 2 opções gravadas neste contrato.`;
    }

    lista.innerHTML = cenarios.map((c, i) => {
        const totalMaq = c.qtdEscavadeiras + c.qtdCaminhoes + c.qtdPatrol + c.qtdTrator;
        return `
            <div class="memorial-item" style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <small>OPÇÃO ${i + 1} • ${c.nomePiso.split('/')[0].trim()} (+${c.inputs.margemFalhaPct}% reserva)</small>
                    <strong>${c.nome} — ${totalMaq} máquinas (MF: ${c.matchFactor.toFixed(2)} | ${c.passadas} passes)</strong>
                </div>
                <div style="white-space: nowrap;">
                    <button type="button" class="btn-acao-tabela" onclick="carregarCenarioNoFormulario(${c.id})" title="Carregar no formulário">🔄</button>
                    <button type="button" class="btn-acao-tabela btn-excluir" onclick="removerCenarioCache(${c.id})" title="Remover opção">✖</button>
                </div>
            </div>
        `;
    }).join('');
}

function renderizarPaginaComparativaDupla() {
    const container = document.getElementById('container-comparativo-duplo');
    if (!container) return;

    const cenarios = obterCenariosCache();
    if (cenarios.length === 0) {
        container.style.gridTemplateColumns = '1fr';
        container.innerHTML = `
            <div class="diagnostico-box" style="text-align: center; padding: 40px;">
                <div class="diagnostico-titulo">Nenhuma opção gravada para comparação</div>
                <p style="color: #94a3b8; margin-top: 8px;">Volte à tela de Dimensionamento de Frota, simule até 2 configurações e clique em "Gravar Opção".</p>
            </div>
        `;
        return;
    }

    let melhorId = null;
    let menorDesvio = Infinity;
    cenarios.forEach(c => {
        if (c.passadas >= 3 && c.passadas <= 5) {
            const desvio = Math.abs(1.0 - c.matchFactor);
            if (desvio < menorDesvio) {
                menorDesvio = desvio;
                melhorId = c.id;
            }
        }
    });

    const base = cenarios[0];
    const totalMaqBase = base.qtdEscavadeiras + base.qtdCaminhoes + base.qtdPatrol + base.qtdTrator;

    container.innerHTML = cenarios.map((c, index) => {
        const totalMaq = c.qtdEscavadeiras + c.qtdCaminhoes + c.qtdPatrol + c.qtdTrator;
        const capCargaTotal = c.qtdEscavadeiras * c.prodEscavadeiraTH;
        const capTranspTotal = c.qtdCaminhoes * c.prodPorCaminhaoTH;
        const folgaTranspPct = RITMO_ALVO_TH > 0 ? (((capTranspTotal - RITMO_ALVO_TH) / RITMO_ALVO_TH) * 100) : 0;
        const kmAno = c.kmTotalHora * HORAS_UTEIS_ANO;

        const mfClass = (c.matchFactor >= 0.95 && c.matchFactor <= 1.05) ? 'mf-ok' :
                        (c.matchFactor < 0.95 ? 'mf-alerta' : 'mf-saturado');
        const passesClass = (c.passadas >= 3 && c.passadas <= 5) ? 'mf-ok' : 'mf-saturado';
        const isMelhor = (c.id === melhorId && cenarios.length > 1);

        const diffMaq = totalMaq - totalMaqBase;
        const diffKmPct = base.kmTotalHora > 0 ? (((c.kmTotalHora - base.kmTotalHora) / base.kmTotalHora) * 100) : 0;

        const badgeComparativo = index === 0
            ? `<span class="badge-classe">OPÇÃO 1 (BASE)</span>`
            : `<span class="badge-classe" style="color: ${diffMaq <= 0 ? '#4ade80' : '#facc15'};">
                 OPÇÃO 2 (${diffMaq > 0 ? '+' : ''}${diffMaq} máq. | ${diffKmPct > 0 ? '+' : ''}${diffKmPct.toFixed(0)}% km)
               </span>`;

        return `
            <fieldset style="margin-bottom: 0; border: 2px solid ${isMelhor ? '#10b981' : '#26334d'}; display: flex; flex-direction: column; gap: 16px;">
                <legend style="font-size: 1.05rem;">
                    ${c.nome} ${isMelhor ? '<span class="badge-recomendado">⭐ MELHOR EQUILÍBRIO</span>' : ''}
                </legend>

                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                    <span style="font-size: 0.9rem; color: #94a3b8;">Piso: <strong style="color: #f8fafc;">${c.nomePiso}</strong> (+${c.inputs.margemFalhaPct}% reserva)</span>
                    ${badgeComparativo}
                </div>

                <div class="subgrid-2">
                    <div class="memorial-item" style="border-left-color: #38bdf8;">
                        <small>Frota Total Mobilizada</small>
                        <strong style="font-size: 1.25rem;">${totalMaq} equipamentos</strong>
                    </div>
                    <div class="memorial-item" style="border-left-color: #10b981;">
                        <small>Acoplamento & Match Factor</small>
                        <strong style="font-size: 1.25rem;" class="${mfClass}">MF ${c.matchFactor.toFixed(2)} <span class="${passesClass}">(${c.passadas} passes)</span></strong>
                    </div>
                </div>

                <div class="card-equipamento" style="gap: 10px;">
                    <div class="card-equipamento-header">
                        <span class="titulo-eq">1. Carga (Escavadeiras)</span>
                        <strong>${c.qtdEscavadeiras} unidades</strong>
                    </div>
                    <div style="font-size: 0.9rem; color: #cbd5e1;">
                        <strong>Modelo:</strong> ${c.inputs.modEscav || 'Não especificado'}<br>
                        <strong>Especificação:</strong> Caçamba ${c.inputs.cacamba} m³ | Ciclo ${c.inputs.cicloEscav}s | Prod. Unitária: ${c.prodEscavadeiraTH.toFixed(0)} t/h<br>
                        <strong>Capacidade Total Carga:</strong> <span class="destaque-ritmo">${capCargaTotal.toFixed(0)} t/h</span>
                    </div>
                </div>

                <div class="card-equipamento" style="gap: 10px;">
                    <div class="card-equipamento-header">
                        <span class="titulo-eq">2. Transporte (Caminhões)</span>
                        <strong>${c.qtdCaminhoes} unidades</strong>
                    </div>
                    <div style="font-size: 0.9rem; color: #cbd5e1;">
                        <strong>Modelo:</strong> ${c.inputs.modCam || 'Não especificado'}<br>
                        <strong>Especificação:</strong> Carga útil ${c.inputs.cargaCaminhao} t | Prod. Unitária: ${c.prodPorCaminhaoTH.toFixed(0)} t/h<br>
                        <strong>Capacidade Total Transp.:</strong> <span class="destaque-ritmo">${capTranspTotal.toFixed(0)} t/h (+${folgaTranspPct.toFixed(1)}% sobre alvo)</span>
                    </div>
                </div>

                <div class="card-equipamento" style="gap: 10px;">
                    <div class="card-equipamento-header">
                        <span class="titulo-eq">3. Infraestrutura, Apoio e Rodagem</span>
                        <strong>${c.qtdPatrol + c.qtdTrator} unidades</strong>
                    </div>
                    <div style="font-size: 0.9rem; color: #cbd5e1;">
                        <strong>Motoniveladoras:</strong> ${c.qtdPatrol}x ${c.inputs.modPatrol || 'Patrol'} (Pista ${c.inputs.extensaoPista} km)<br>
                        <strong>Tratores de Esteiras:</strong> ${c.qtdTrator}x ${c.inputs.modTrator || 'Trator'}<br>
                        <strong>Rodagem Estimada:</strong> <span style="color: #f8fafc; font-weight: 700;">${c.kmTotalHora.toFixed(1)} km/h</span> (${kmAno.toLocaleString('pt-BR', { maximumFractionDigits: 0 })} km/ano)
                    </div>
                </div>
            </fieldset>
        `;
    }).join('');
}

document.addEventListener('DOMContentLoaded', renderizarTabelaComparativa);