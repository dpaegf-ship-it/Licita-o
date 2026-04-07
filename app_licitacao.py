#!/usr/bin/env python3
"""Aplicativo desktop (Tkinter) para conduzir o rito e gerar ZIP das peças."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox


class AppLicitacao:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Automação de Peças de Licitação")
        self.root.geometry("900x620")

        self.base_dir = Path(__file__).resolve().parent
        self.modelos_dir = self.base_dir / "modelos"
        self.dados_path = self.base_dir / "dados" / "exemplo.json"
        self.rito_path = self.base_dir / "dados" / "rito_cmmdo.json"
        self.saida_dir = self.base_dir / "saida"

        self.etapas: list[dict] = []

        self._montar_tela()
        self.recarregar_rito()

    def _montar_tela(self) -> None:
        frame_top = tk.Frame(self.root)
        frame_top.pack(fill="x", padx=12, pady=8)

        tk.Label(frame_top, text="Dados JSON:").grid(row=0, column=0, sticky="w")
        self.var_dados = tk.StringVar(value=str(self.dados_path))
        tk.Entry(frame_top, textvariable=self.var_dados, width=85).grid(row=0, column=1, padx=6)
        tk.Button(frame_top, text="Selecionar", command=self.selecionar_dados).grid(row=0, column=2)

        tk.Label(frame_top, text="Rito JSON:").grid(row=1, column=0, sticky="w")
        self.var_rito = tk.StringVar(value=str(self.rito_path))
        tk.Entry(frame_top, textvariable=self.var_rito, width=85).grid(row=1, column=1, padx=6)
        tk.Button(frame_top, text="Selecionar", command=self.selecionar_rito).grid(row=1, column=2)

        frame_buttons = tk.Frame(self.root)
        frame_buttons.pack(fill="x", padx=12, pady=6)

        tk.Button(frame_buttons, text="1) Recarregar rito", command=self.recarregar_rito).pack(side="left", padx=4)
        tk.Button(frame_buttons, text="2) Próxima etapa", command=self.mostrar_proxima_etapa).pack(side="left", padx=4)
        tk.Button(frame_buttons, text="3) Inserir arquivos da etapa", command=self.inserir_arquivos_etapa).pack(side="left", padx=4)
        tk.Button(frame_buttons, text="4) Gerar etapa", command=self.gerar_etapa_atual).pack(side="left", padx=4)
        tk.Button(frame_buttons, text="5) Gerar ZIP final", command=self.gerar_zip_final).pack(side="left", padx=4)

        self.lbl_status = tk.Label(self.root, text="Status: pronto", anchor="w", fg="#0a3d62")
        self.lbl_status.pack(fill="x", padx=12, pady=4)

        self.txt_log = tk.Text(self.root, height=28)
        self.txt_log.pack(fill="both", expand=True, padx=12, pady=8)
        self.log("Aplicativo iniciado. Clique em 'Próxima etapa'.")

    def log(self, texto: str) -> None:
        self.txt_log.insert("end", f"{texto}\n")
        self.txt_log.see("end")

    def selecionar_dados(self) -> None:
        caminho = filedialog.askopenfilename(title="Selecionar JSON de dados", filetypes=[("JSON", "*.json")])
        if caminho:
            self.var_dados.set(caminho)

    def selecionar_rito(self) -> None:
        caminho = filedialog.askopenfilename(title="Selecionar JSON do rito", filetypes=[("JSON", "*.json")])
        if caminho:
            self.var_rito.set(caminho)

    def recarregar_rito(self) -> None:
        try:
            rito_path = Path(self.var_rito.get())
            rito = json.loads(rito_path.read_text(encoding="utf-8"))
            self.etapas = rito.get("etapas", [])
            if not self.etapas:
                raise ValueError("Rito sem etapas")
            self.lbl_status.config(text=f"Status: rito carregado com {len(self.etapas)} etapas")
            self.log(f"Rito carregado: {rito_path}")
        except Exception as exc:
            messagebox.showerror("Erro", f"Falha ao carregar rito: {exc}")

    def _arquivos_esperados(self, etapa: dict) -> list[str]:
        arquivos: list[str] = []
        modelo = etapa.get("modelo")
        anexos = etapa.get("anexos")
        if isinstance(modelo, str) and modelo.strip():
            arquivos.append(modelo.strip())
        if isinstance(anexos, list):
            for item in anexos:
                if isinstance(item, str) and item.strip():
                    arquivos.append(item.strip())
        return arquivos

    def _proxima_etapa_pendente(self) -> tuple[dict | None, list[str]]:
        for etapa in self.etapas:
            faltantes = [arq for arq in self._arquivos_esperados(etapa) if not (self.modelos_dir / arq).exists()]
            if faltantes:
                return etapa, faltantes
        return None, []

    def mostrar_proxima_etapa(self) -> None:
        etapa, faltantes = self._proxima_etapa_pendente()
        if etapa is None:
            self.lbl_status.config(text="Status: nenhuma etapa pendente")
            self.log("Todas as etapas possuem arquivos em modelos/.")
            return

        self.lbl_status.config(text=f"Status: próxima etapa -> {etapa.get('nome')}")
        self.log(f"Próxima etapa: {etapa.get('nome')}")
        self.log("Arquivos pendentes:")
        for arq in faltantes:
            self.log(f" - {arq}")

    def inserir_arquivos_etapa(self) -> None:
        etapa, faltantes = self._proxima_etapa_pendente()
        if etapa is None:
            messagebox.showinfo("Etapas", "Não há etapas pendentes.")
            return

        for esperado in faltantes:
            origem = filedialog.askopenfilename(title=f"Selecione o arquivo para: {esperado}")
            if not origem:
                self.log(f"Arquivo não selecionado para {esperado}.")
                return
            destino = self.modelos_dir / esperado
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origem, destino)
            self.log(f"Copiado: {origem} -> {destino}")

        self.mostrar_proxima_etapa()

    def gerar_etapa_atual(self) -> None:
        etapa, _faltantes = self._proxima_etapa_pendente()
        if etapa is None:
            messagebox.showinfo("Etapas", "Não há etapa pendente para gerar.")
            return

        cmd = [
            sys.executable,
            str(self.base_dir / "scripts" / "gerar_pecas.py"),
            "--dados",
            self.var_dados.get(),
            "--modelos",
            str(self.modelos_dir),
            "--saida",
            str(self.saida_dir),
            "--rito",
            self.var_rito.get(),
            "--etapa",
            str(etapa.get("nome")),
        ]

        self.log(f"Executando: {' '.join(cmd)}")
        resultado = subprocess.run(cmd, capture_output=True, text=True)
        if resultado.stdout:
            self.log(resultado.stdout.strip())
        if resultado.returncode != 0:
            self.log(resultado.stderr.strip())
            messagebox.showerror("Erro na geração", resultado.stderr.strip() or "Falha na geração")
            return

        self.log("Etapa gerada com sucesso.")
        self.mostrar_proxima_etapa()

    def gerar_zip_final(self) -> None:
        if not self.saida_dir.exists():
            messagebox.showwarning("Atenção", "A pasta saida/ ainda não existe. Gere ao menos uma etapa.")
            return

        zip_path = self.base_dir / "saida_licitacao.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as arquivo_zip:
            for arquivo in self.saida_dir.rglob("*"):
                if arquivo.is_file():
                    arquivo_zip.write(arquivo, arquivo.relative_to(self.saida_dir))

        self.log(f"ZIP final gerado: {zip_path}")
        messagebox.showinfo("Concluído", f"ZIP gerado em:\n{zip_path}")


def main() -> int:
    root = tk.Tk()
    AppLicitacao(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
