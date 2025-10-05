// script.js — carregamento do gráfico e diagnóstico
async function carregarGrafico(meses = 1) {
  const totalDiv = document.getElementById("totalGeral");
  try {
    console.log("Carregando gráfico para", meses, "mes(es)...");
const resp = await fetch(`/api/gastos-mensais?meses=${meses}&t=${Date.now()}`, {
  cache: "no-store"
});
    const dados = await resp.json();
    console.log("Resposta API:", dados);

    if (dados.erro) {
      totalDiv.innerText = "Erro: " + dados.erro;
      return;
    }

    const categorias = (dados.categorias || []).map(i => i.categoria);
    const valores = (dados.categorias || []).map(i => parseFloat(i.total || 0));

    // total geral
    totalDiv.innerText = `💰 Total (${meses} mês(es)): R$ ${Number(dados.total_geral || 0).toFixed(2)}`;

    // se não houver dados, mostra mensagem e limpa gráfico
    if (!categorias.length) {
      if (window.meuGrafico) window.meuGrafico.destroy();
      const ctxEmpty = document.getElementById("graficoGastos").getContext("2d");
      // desenha um "gráfico vazio" com uma fatia e legenda "Sem dados"
      if (window.meuGrafico) window.meuGrafico = null;
      window.meuGrafico = new Chart(ctxEmpty, {
        type: "pie",
        data: {
          labels: ["Sem dados"],
          datasets: [{ data: [1], backgroundColor: ["#555555"], borderColor: "#fff" }]
        },
        options: { plugins: { legend: { labels: { color: "white" } } } }
      });
      return;
    }

    const ctx = document.getElementById("graficoGastos").getContext("2d");
    if (window.meuGrafico) window.meuGrafico.destroy();

    window.meuGrafico = new Chart(ctx, {
      type: "pie",
      data: {
        labels: categorias,
        datasets: [{
          data: valores,
          backgroundColor: ["#ff66c4", "#7209b7", "#3a0ca3", "#f72585", "#b5179e", "#4895ef"],
          borderColor: "#fff",
          borderWidth: 2
        }]
      },
      options: {
        plugins: {
          legend: { position: "bottom", labels: { color: "white", font: { size: 14 } } }
        }
      }
    });

  } catch (err) {
    console.error("Erro carregarGrafico:", err);
    document.getElementById("totalGeral").innerText = "Erro ao carregar gráfico (veja console).";
  }
}

// debug: busca últimos registros e mostra no console
async function debugUltimosRegistros() {
  try {
    const resp = await fetch('/api/test-gastos');
    const rows = await resp.json();
    console.log("Últimos registros (debug):", rows);
    alert("Veja console (F12) para os últimos registros.");
  } catch (e) {
    console.error("Erro debug:", e);
    alert("Erro no debug, veja console.");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  // inicial
  carregarGrafico(1);

  // mudança de período
  const sel = document.getElementById("periodoGrafico");
  sel.addEventListener("change", (e) => {
    const meses = parseInt(e.target.value, 10) || 1;
    carregarGrafico(meses);
  });

  // botão debug
  const bt = document.getElementById("bt-debug");
  bt.addEventListener("click", debugUltimosRegistros);
});
