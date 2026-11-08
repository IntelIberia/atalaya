#!/usr/bin/env python3
"""Tests de scripts/check_spec.py: cada test inyecta un fallo en una copia de los
documentos y comprueba que la verificación falla con el error esperado.

Uso: python3 -I -m unittest discover -s scripts -p 'test_check_spec.py' -v
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_spec

REPO = Path(__file__).resolve().parent.parent


class CheckSpecTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(REPO / "docs", self.tmp / "docs")
        (self.tmp / "scripts").mkdir()
        shutil.copy(REPO / check_spec.ALLOWLIST_REL, self.tmp / check_spec.ALLOWLIST_REL)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp)

    def run_check(self) -> tuple[int, str]:
        lines: list[str] = []
        code = check_spec.run(self.tmp, out=lines.append)
        return code, "\n".join(lines)

    def edit(self, rel: str, old: str, new: str) -> None:
        p = self.tmp / rel
        text = p.read_text(encoding="utf-8")
        self.assertIn(old, text, f"el fragmento a sustituir no está en {rel}")
        p.write_text(text.replace(old, new, 1), encoding="utf-8")

    def append(self, rel: str, line: str) -> None:
        with (self.tmp / rel).open("a", encoding="utf-8") as f:
            f.write("\n" + line + "\n")

    # --- línea base -------------------------------------------------------------
    def test_repositorio_actual_pasa(self) -> None:
        code, out = self.run_check()
        self.assertEqual(code, 0, out)

    # --- requisitos -------------------------------------------------------------
    def test_must_sin_metodo_falla(self) -> None:
        self.edit(
            check_spec.REQ_REL,
            "sin pérdidas ni duplicados | T | 1 |",
            "sin pérdidas ni duplicados |  | 1 |",
        )
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("REQ-FUN-001: MUST sin método válido", out)

    def test_id_duplicado_falla(self) -> None:
        self.edit(check_spec.REQ_REL, "| REQ-FUN-002 | MUST |", "| REQ-FUN-001 | MUST |")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("ID duplicado: REQ-FUN-001", out)

    def test_prioridad_invalida_falla(self) -> None:
        self.edit(check_spec.REQ_REL, "| REQ-FUN-003 | MUST |", "| REQ-FUN-003 | MAYBE |")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("prioridad no válida", out)

    # --- casos de uso y referencias --------------------------------------------
    def test_cu_con_requisito_inexistente_falla(self) -> None:
        self.edit(
            check_spec.SPEC_REL,
            "**Requisitos:** REQ-LEG-008\n",
            "**Requisitos:** REQ-LEG-008, REQ-FUN-999\n",
        )
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("CU-15: referencia un requisito inexistente REQ-FUN-999", out)

    def test_requisito_huerfano_falla(self) -> None:
        self.append(check_spec.REQ_REL, "| REQ-FUN-998 | COULD | Huérfano | c | T | 1 | j |")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("REQ-FUN-998: no lo referencia ningún caso de uso", out)

    def test_referencia_ver_inexistente_falla(self) -> None:
        self.append("docs/PLAN-MAESTRO-DE-PRUEBAS.md", "Ver REQ-SEC-777.")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("cita un requisito inexistente REQ-SEC-777", out)

    # --- correspondencia y estructura ------------------------------------------
    def test_falta_restriccion_legal_en_correspondencia_falla(self) -> None:
        self.edit(check_spec.REQ_REL, "| LEGAL-5 |", "| OTRA-5 |")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("falta la fila LEGAL-5", out)

    def test_falta_rol_falla(self) -> None:
        self.edit(check_spec.SPEC_REL, "| Auditor | Control interno", "| Revisor | Control interno")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("falta el rol «Auditor»", out)

    def test_falta_seccion_fuera_de_alcance_falla(self) -> None:
        self.edit(check_spec.SPEC_REL, "## 4. Fuera de alcance", "## 4. Exclusiones")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("falta la sección «Fuera de alcance»", out)

    def test_falta_categoria_de_riesgo_hardware_falla(self) -> None:
        p = self.tmp / check_spec.RISK_REL
        text = p.read_text(encoding="utf-8").replace("| Hardware |", "| Otro |")
        p.write_text(text, encoding="utf-8")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("ningún riesgo de categoría «Hardware»", out)

    # --- guardarraíl legal (frases que colaban con la versión anterior) ----------
    def assert_legal_flagged(self, sentence: str) -> None:
        self.append(check_spec.SPEC_REL, sentence)
        code, out = self.run_check()
        self.assertEqual(code, 1, f"no se detectó: {sentence}")
        self.assertIn("mención sensible no revisada", out)

    def test_inhibir_con_no_en_la_frase_se_detecta(self) -> None:
        self.assert_legal_flagged("El nodo inhibe el dron si no hay confirmación.")

    def test_interfiere_se_detecta(self) -> None:
        self.assert_legal_flagged("El módulo interfiere el enlace de vídeo.")

    def test_neutralice_se_detecta(self) -> None:
        self.assert_legal_flagged("Se propone que el sistema neutralice el objetivo.")

    def test_transmite_se_detecta(self) -> None:
        self.assert_legal_flagged("El SDR transmite una señal en 2,4 GHz.")

    def test_tx_se_detecta(self) -> None:
        self.assert_legal_flagged("Activar TX en el Pluto para calibrar.")

    def test_demodular_droneid_se_detecta(self) -> None:
        self.assert_legal_flagged("Decodificar DroneID para obtener el número de serie.")

    def test_persistir_audio_se_detecta(self) -> None:
        self.assert_legal_flagged("El nodo puede persistir el audio para depurar.")

    def test_atribucion_automatica_se_detecta(self) -> None:
        self.assert_legal_flagged("La fusión hace la atribución automática del país.")

    def test_publicar_datos_de_pilotos_se_detecta(self) -> None:
        self.assert_legal_flagged("El radar muestra datos de pilotos cercanos.")

    def test_linea_revisada_modificada_vuelve_a_fallar(self) -> None:
        self.edit(
            check_spec.SPEC_REL,
            "- Publicar datos de pilotos u operadores (REQ-LEG-007).",
            "- Publicar datos de pilotos u operadores cuando convenga (REQ-LEG-007).",
        )
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("mención sensible no revisada", out)


if __name__ == "__main__":
    unittest.main()
