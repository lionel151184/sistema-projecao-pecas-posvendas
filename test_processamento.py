import unittest
from unittest.mock import patch

import pandas as pd

from processamento import carregar_base


class CarregarBaseTests(unittest.TestCase):
    def base(self):
        return pd.DataFrame({
            "Casos": [1, 2, 3],
            "Modelo": ["Modelo A"] * 3,
            "Data de criação": ["01/01/2025", "02/01/2025", "03/01/2025"],
            "Descrição da Peça": ["Peça A"] * 3,
            "Código do item: Código": ["P001"] * 3,
            "Estado": ["PR"] * 3,
            "Cidade": ["Cidade A"] * 3,
        })

    def carregar(self, base):
        with patch("processamento.pd.read_excel", return_value=base):
            return carregar_base()

    def test_conta_linhas_em_vez_de_somar_numeracao(self):
        df = self.carregar(self.base())
        self.assertEqual(df["Ocorrências"].tolist(), [1, 1, 1])
        self.assertEqual(df.groupby("CódigoPeça")["Ocorrências"].sum()["P001"], 3)
        self.assertNotIn("Quantidade", df.columns)

    def test_numeracao_repetida_nao_deduplica_linhas(self):
        base = self.base()
        base["Casos"] = [10, 10, 30]
        self.assertEqual(self.carregar(base)["Ocorrências"].sum(), 3)

    def test_quantidade_antiga_nao_altera_contagem(self):
        base = self.base()
        base["Qtd_peças_SVO"] = [20, 30, 40]
        self.assertEqual(self.carregar(base)["Ocorrências"].sum(), 3)

    def test_datas_invalidas_continuam_excluidas(self):
        base = self.base()
        base.loc[1, "Data de criação"] = "invalida"
        self.assertEqual(self.carregar(base)["Ocorrências"].sum(), 2)

    def test_cabecalhos_ausentes_tem_mensagem_explicita(self):
        base = self.base().drop(columns=["Casos", "Descrição da Peça"])
        with self.assertRaisesRegex(ValueError, "Casos, Descrição da Peça"):
            self.carregar(base)


if __name__ == "__main__":
    unittest.main()
