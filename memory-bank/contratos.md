# Contratos

**Estado: implementado em `src/core/core/{caso,modelo,docs,politica}.py`, com testes.** Congela na hora 2 do evento. Depois disso, mudança exige editar este arquivo no mesmo commit e avisar o grupo. Tudo aqui vive em `src/core` e depende só de pydantic e numpy.

Fronteira **arquivo primeiro**: P1 e P3 são chamados pelo job `ingest`, mas cada um também grava sua saída em `data/derived/`. O ingest prefere o arquivo se existir. Import quebrado não derruba a API.

## Caso (entrada comum)
```python
class Subsidios(BaseModel):
    contrato: bool = False; extrato: bool = False; comprovante_credito: bool = False
    dossie: bool = False; demonstrativo_divida: bool = False; laudo_referenciado: bool = False

class CasoFeatures(BaseModel):
    numero: str; uf: str; sub_assunto: str | None; valor_causa: float
    subsidios: Subsidios       # .presentes(), .ausentes(), .n
    sinais: dict = {}          # extras de P3 (codigo -> valor); valor verdadeiro = sinal ativo
```
`core/caso.py` também tem `CODIGOS_SINAIS` (código → descrição) e `NOMES_SUBSIDIOS` (flag → nome legível).

## P1 modelo (`core/modelo.py`)
```python
class Contribuicao(BaseModel): feature: str; valor: str | float | bool | None; contribuicao: float; descricao: str | None = None

class Scores(BaseModel):
    numero: str; modelo_versao: str; origem: Literal["modelo", "stub"]
    p_exito_defesa: float                                   # P(banco vence), 0..1
    condenacao_p20: float; condenacao_p50: float; condenacao_p80: float   # condicionais a perder
    contribuicoes: list[Contribuicao] = []                  # top 5, com sinal
    gerado_em: datetime

class CalibracaoBin(BaseModel): p_min: float; p_max: float; n: int; p_prevista_media: float; taxa_exito_real: float
class ModeloInfo(BaseModel): versao: str; treinado_em: datetime; n_treino: int; metricas: dict[str, float]; calibracao: list[CalibracaoBin] = []; importancias: dict[str, float] = {}

class ModeloScores(Protocol):
    def score(self, caso: CasoFeatures) -> Scores: ...
    def score_batch(self, casos: list[CasoFeatures]) -> list[Scores]: ...
    def info(self) -> ModeloInfo: ...
```
P1 também entrega `data/derived/historico_scored.csv` (local, não versionado; decisão 19) com colunas fixas em snake_case: `numero, uf, sub_assunto, resultado_macro (1/0), resultado_micro, valor_causa, valor_condenacao, contrato, extrato, comprovante_credito, dossie, demonstrativo_divida, laudo_referenciado, p_exito_oof, condenacao_p20_oof, condenacao_p50_oof, condenacao_p80_oof, fold`.
P1 exporta ainda o modelo treinado em JSON ou UBJ do XGBoost em `src/model/artifacts/` (versionado), para o clone limpo subir com scores reais sem a base.

## P3 extração (`core/docs.py`)
```python
class Pessoa(BaseModel): nome: str | None; cpf_mascarado: str | None; idade: int | None; email: str | None; telefone: str | None
class Advogado(Pessoa): oab: str | None
class ContratoInfo(BaseModel):
    canal: Literal["app", "internet_banking", "agencia", "correspondente", "telefone", "desconhecido"] = "desconhecido"
    assinatura: Literal["fisica", "digital", "biometria", "ausente", "desconhecida"] = "desconhecida"
    credito_conta_terceiro: bool | None; valor: float | None; parcelas: int | None; data: date | None
class SinalAlerta(BaseModel): codigo: str; descricao: str; severidade: Literal["baixa", "media", "alta"]; fonte: str | None
# códigos previstos: IDOSO, CREDITO_CONTA_TERCEIRO, BOLETIM_OCORRENCIA, RECLAMACAO_BACEN, SEM_CONTRATO, ASSINATURA_DIVERGENTE, CANAL_DIGITAL_SEM_PERFIL

class DadosExtraidos(BaseModel):
    numero: str; origem: Literal["llm", "stub"]; modelo: str | None
    autor: Pessoa; advogado_autor: Advogado; comarca: str | None; uf: str | None
    valor_causa: float | None; pedidos: list[str] = []; contrato: ContratoInfo = ContratoInfo()
    sinais_alerta: list[SinalAlerta] = []; resumo_fatos: str = ""; confianca: float = 0.0; gerado_em: datetime

class Analise(BaseModel):     # independe da decisão; nunca fica obsoleta
    numero: str; origem: str; pontos_fortes_banco: list[str]; pontos_fracos_banco: list[str]
    tese_provavel_autor: str; riscos: list[str]; texto: str

class Minutas(BaseModel):     # depende da recomendação; guarda politica_id
    numero: str; politica_id: int | None; origem: str; proposta_acordo: str; roteiro_defesa: str; mensagem_contato: str

class ExtratorDocs(Protocol):
    def extrair(self, processo_dir: Path, numero: str) -> DadosExtraidos: ...
    def analisar(self, caso: CasoFeatures, dados: DadosExtraidos, scores: Scores) -> Analise: ...
    def redigir(self, caso: CasoFeatures, dados: DadosExtraidos, rec: Recomendacao) -> Minutas: ...
```
`core/docs.py` também tem `subsidios_por_arquivos(nomes) -> Subsidios`: deduz as seis flags pelos nomes dos PDFs da pasta `subsidios/`. O ingest usa isso; P3 pode reutilizar.

## Política (`core/politica.py`, dona: API; P1 calibra os defaults)
```python
class PoliticaParams(BaseModel):
    custas_fixas_defesa: float = 1500; honorarios_defesa_pct: float = 0.10; sucumbencia_pct: float = 0.10
    custo_operacional_acordo: float = 300; taxa_aceite_esperada: float = 0.65
    fator_oferta: float = 0.80            # fração do prejuízo esperado (q · cond_p50) que vira oferta
    piso_oferta_pct_causa: float = 0.10; teto_oferta_pct_causa: float = 0.60
    margem_banda_pct: float = 0.15; arredondamento: float = 50
    limiar_defesa_forte: float = 0.85; limiar_acordo_forte: float = 0.30
    sinais_forcam_acordo: list[str] = ["CREDITO_CONTA_TERCEIRO"]
    valor_causa_max_sem_aprovacao: float | None = 50000
    incluir_extincao_no_backtest: bool = True

class Recomendacao(BaseModel):
    tipo: Literal["acordo", "defesa"]; valor_sugerido: float | None; valor_min: float | None; valor_max: float | None
    custo_esperado_defesa: float; custo_esperado_acordo: float; economia_esperada: float
    regra: Literal["defesa_forte", "acordo_forte", "custo", "sinal"]; sinais_acionados: list[str] = []
    motivos: list[str]; scores_snapshot: Scores; politica_id: int
```
Validação dos params: `limiar_acordo_forte ≤ limiar_defesa_forte`, `piso ≤ teto`, `arredondamento > 0`.
Funções: `calcular(p_exito, p20, p50, p80, valor_causa, prm, sinais_forcam=None)` → dict de arrays (`acordo, oferta, valor_min, valor_max, custo_defesa, custo_acordo, economia, regra, oferta_limitada`); `custos_reais(..., perdeu, valor_condenacao, prm)` acrescenta `custo_defesa_real, custo_acordo_real, custo_politica` para o backtest; `aplicar(scores, caso, prm, politica_id) -> Recomendacao` com 3 motivos determinísticos em português.
Fórmula (uma implementação em numpy, serve escalar e coluna):
```
q             = 1 - p_exito
custo_defesa  = custas_fixas + honorarios_pct·valor_causa + q·cond_p50·(1 + sucumbencia_pct)
oferta        = round(fator_oferta·q·cond_p50), limitada a [piso·causa, min(teto·causa, cond_p80)] e arredondada de novo ao `arredondamento`
custo_acordo  = a·(oferta + op) + (1 − a)·(custo_defesa + op)          # a = taxa_aceite_esperada
tipo          = defesa se p_exito ≥ limiar_defesa_forte; acordo se p_exito ≤ limiar_acordo_forte;
                senão acordo se custo_acordo < custo_defesa; sinal em sinais_forcam_acordo força acordo
banda         = oferta·(1 ± margem_banda_pct)
```
Backtest usa **resultados reais**: `custo_defesa_real = custas + hon·causa + condenação·(1 + sucumb) se perdeu`. Baselines "defender tudo" e "acordar tudo" lado a lado.

## Seleção de implementação
Env `MODEL_IMPL=model.predict:Modelo` e `EXTRACTOR_IMPL=extractor.pipeline:Extrator`. A classe precisa ser instanciável **sem argumentos** (carrega seus artefatos sozinha). Import ou construção falha → stub, log alto, campo `origem` mostra "stub" na UI. `app/plugins.py` faz isso no start e em `POST /api/internal/reload-historico`.
