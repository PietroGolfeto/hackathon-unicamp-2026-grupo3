from __future__ import annotations

import pytest

from enteros import config as cfg
from enteros.policy.engine import Engine
from enteros.schemas import CaseFeatures, DocsStatus

TODOS_PRESENTES = DocsStatus(**{d: cfg.STATUS_PRESENTE for d in cfg.DOCS})


@pytest.fixture(scope="session")
def engine() -> Engine:
    return Engine.carregar()


@pytest.fixture
def caso_01() -> CaseFeatures:
    """Arquétipo do Caso 01 (São Luís/MA): 6 subsídios, crédito na conta da autora, biometria e assinatura ok."""
    return CaseFeatures(
        numero="0801234-56.2024.8.10.0001", uf="MA", sub_assunto=cfg.SUB_GENERICO, valor_causa=20000.0,
        docs=TODOS_PRESENTES, conta_deposito_titular_autor=True, liveness_presente=True,
        parcelas_pagas=20, valor_parcela=120.0, saldo_devedor=6240.0, dano_moral_pedido=15000.0,
        contradicoes=["Petição nega uso dos valores; extrato mostra TED, PIX e saque após o crédito"],
    )


@pytest.fixture
def caso_02() -> CaseFeatures:
    """Arquétipo do Caso 02 (Manaus/AM): sem contrato, sem extrato, crédito em conta de terceiro, liveness ausente."""
    return CaseFeatures(
        numero="0654321-09.2024.8.04.0001", uf="AM", sub_assunto=cfg.SUB_GOLPE, valor_causa=25000.0,
        docs=DocsStatus(comprovante=cfg.STATUS_PRESENTE, demonstrativo=cfg.STATUS_PRESENTE, laudo=cfg.STATUS_PRESENTE),
        conta_deposito_titular_autor=False, liveness_presente=False,
        parcelas_pagas=8, valor_parcela=180.0, saldo_devedor=2748.38, dano_moral_pedido=18000.0,
        red_flags=["BOLETIM_OCORRENCIA", "RECLAMACAO_BACEN"],
    )
