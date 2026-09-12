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
# códigos previstos: IDOSO, CREDITO_CONTA_TERCEIRO, BOLETIM_OCORRENCIA, RECLAMACAO_BACEN, SEM_CONTRATO, ASSINATURA_DIVERGENTE,
#   CANAL_DIGITAL_SEM_PERFIL, LIVENESS_AUSENTE_CANAL_DIGITAL (canal digital sem vídeo de liveness), DOCUMENTO_SUSPEITO (emitido pelo
#   extractor, não pelo LLM: PDF com script/ação/anexo ou texto com instrução embutida; o trecho sai do brief e o arquivo vai em `fonte`)

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
Env `MODEL_IMPL=model.predict:Modelo` e `EXTRACTOR_IMPL=extractor.pipeline:Extrator`. A classe precisa ser instanciável **sem argumentos** (carrega seus artefatos sozinha). Import ou construção falha, log alto: o modelo cai em `StubModelo` (campo `origem` mostra "stub" na UI); o extrator vira `None` e nada é extraído, analisado ou redigido (decisão 27). `app/plugins.py` faz isso no start e em `POST /api/internal/reload-historico`.

Extractor real (padrão): `EXTRACTOR_IMPL=extractor.pipeline:Extrator`. Env: `OPENAI_API_KEY`, `OPENAI_MODEL` (padrão `gpt-4o-mini`), `EXTRACTOR_CACHE_DIR` (padrão `DATA_DIR/cache/extractor`). Sem chave, `Extrator()` constrói e serve só do cache; `extrair` sem cache levanta `ErroConfiguracao` (o ingest para avisando). `extrair` e `analisar` vêm da mesma chamada ao LLM; `redigir` é template. Campos que o LLM devolve além do contrato (`dano_moral_pedido`, `valor_parcela`, `parcelas_pagas`, `saldo_devedor`, `liveness`, `banco_deposito`, `canal_alegado_pelo_autor`, `contradicoes`) ficam no cache (`saida_llm`) e no `texto` da análise; entram no contrato quando P1/P4 precisarem (mudança aditiva). `SinalAlerta.codigo` pode ser `OUTRO` com a descrição.

## O que P1 entregou na fase 1 (`src/enteros`, pacote `enteros`)
Contratos próprios em `enteros/schemas.py`: `CaseFeatures` (uf, sub_assunto, valor_causa, `docs` com status `presente|ausente|inconsistente`, opcionais da IA documental) → `Recomendacao` (decisão `defesa|acordo|instruir`, faixa, `p_perda` e intervalo, condenação p20/p50/p80, `ev_defesa`, `ev_acordo`, escada abertura/alvo/teto, decomposição, VOI, motivos, regras, contribuições). Parâmetros em `enteros/policy/policy.yaml`.

Mapa para o contrato do portal (`core.modelo.Scores`), implementado pelo adapter `src/api/app/modelo_enteros.py` (`ModeloEnteros`, padrão de `MODEL_IMPL`):
| `core` | `enteros` |
|---|---|
| `p_exito_defesa` | `1 − p_perda` (média entre tabela de segmentos e logística) |
| `condenacao_p20/p50/p80` | quantis de `ratio_condenacao` (UF × sub-assunto) × `valor_causa` |
| `contribuicoes` (positivo = favorece o banco) | `ModeloPerda.contribuicoes` com o sinal invertido (lá positivo = mais risco) |
| `ModeloInfo.metricas/calibracao` | `modelo.metricas` (auc_oof, brier_oof, ece_oof, n_treino) e `modelo.calibracao` |
| `Subsidios` (bool) | `DocsStatus` (`presente`/`ausente`; `inconsistente` só vem da IA) |

Mapa `PoliticaParams` (API) ↔ `policy.yaml` (engine), para P1 calibrar os defaults:
| `PoliticaParams` (default) | `policy.yaml` | Nota |
|---|---|---|
| `limiar_defesa_forte` 0,85 | `1 − faixas.limiar_verde` = 0,85 | igual |
| `limiar_acordo_forte` 0,30 | `1 − faixas.limiar_vermelha` = 0,40 | engine acorda mais cedo |
| `custas_fixas_defesa` 1.500 | `custos.custo_escritorio_defesa` 1.200 | |
| `honorarios_defesa_pct` 10% da causa | `custas_pct_valor_causa` 2% + correção `fator_tempo` 1,196 sobre a condenação | estruturas diferentes |
| `sucumbencia_pct` 10% | `honorarios_sucumbencia_pct` 15% | |
| `custo_operacional_acordo` 300 | `custo_escritorio_acordo` 300 | igual |
| `taxa_aceite_esperada` 0,65 fixa | curva logística (`aceite_s50` 30% da causa, largura 0,06) | API mede o aceite real e substitui |
| `fator_oferta` 0,80 × prejuízo esperado | alvo = argmin do custo esperado na grade | |
| `piso/teto_oferta_pct_causa` 10% / 60% | 10% / 70%; teto também ≤ 90% do EV de defesa | |
| `sinais_forcam_acordo` [CREDITO_CONTA_TERCEIRO] | + LIVENESS_AUSENTE_CANAL_DIGITAL | o segundo código já existe em `core/caso.py`; o extractor o emite quando o laudo diz que o liveness não foi localizado em contratação digital |

