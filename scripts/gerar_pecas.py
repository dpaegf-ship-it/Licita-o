#!/usr/bin/env python3
"""Gerador de peças documentais de licitação orientado por rito processual."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

PADRAO_CAMPO = re.compile(r"\{\{\s*([a-zA-Z0-9_\.]+)\s*\}\}")


@dataclass(frozen=True)
class EtapaRito:
    nome: str
    modelos: tuple[str, ...]
    saida: str | None = None


@dataclass(frozen=True)
class TrabalhoGeracao:
    nome_etapa: str
    caminho_modelo: Path
    nome_saida: str


def carregar_json(caminho: Path) -> Dict[str, object]:
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
    with caminho.open("r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def carregar_dados(caminho: Path) -> Dict[str, object]:
    dados = carregar_json(caminho)
    if not isinstance(dados, dict):
        raise ValueError("O JSON de dados deve ser um objeto no nível raiz")
    return dados


def extrair_campos(texto: str) -> List[str]:
    campos = PADRAO_CAMPO.findall(texto)
    vistos: set[str] = set()
    ordenados: List[str] = []
    for campo in campos:
        if campo not in vistos:
            vistos.add(campo)
            ordenados.append(campo)
    return ordenados


def resolver_campo(dados: Dict[str, object], chave: str) -> str:
    valor: object = dados
    for parte in chave.split("."):
        if not isinstance(valor, dict) or parte not in valor:
            raise KeyError(f"Campo '{chave}' não encontrado nos dados")
        valor = valor[parte]
    return str(valor)


def validar_campos_obrigatorios(campos: Sequence[str], dados: Dict[str, object], origem: str) -> None:
    faltantes: List[str] = []
    for campo in campos:
        try:
            resolver_campo(dados, campo)
        except KeyError:
            faltantes.append(campo)

    if faltantes:
        faltantes_txt = ", ".join(sorted(faltantes))
        raise KeyError(f"Campos faltantes para '{origem}': {faltantes_txt}")


def renderizar_modelo(texto: str, dados: Dict[str, object]) -> str:
    def substituir(correspondencia: re.Match[str]) -> str:
        return resolver_campo(dados, correspondencia.group(1))

    return PADRAO_CAMPO.sub(substituir, texto)


def listar_modelos(pasta_modelos: Path) -> List[Path]:
    if not pasta_modelos.exists():
        raise FileNotFoundError(f"Pasta de modelos não encontrada: {pasta_modelos}")

    extensoes_suportadas = {".md", ".txt", ".pdf", ".jpg", ".jpeg", ".png"}
    modelos = sorted([arquivo for arquivo in pasta_modelos.iterdir() if arquivo.is_file() and arquivo.suffix.lower() in extensoes_suportadas])
    if not modelos:
        raise RuntimeError(f"Nenhum modelo suportado encontrado em: {pasta_modelos}")
    return modelos


def carregar_rito(caminho_rito: Path) -> List[EtapaRito]:
    conteudo = carregar_json(caminho_rito)
    etapas_brutas = conteudo.get("etapas") if isinstance(conteudo, dict) else None

    if not isinstance(etapas_brutas, list) or not etapas_brutas:
        raise ValueError("O rito deve ter a chave 'etapas' com uma lista não vazia")

    etapas: List[EtapaRito] = []
    for indice, etapa in enumerate(etapas_brutas, start=1):
        if not isinstance(etapa, dict):
            raise ValueError(f"Etapa {indice} inválida: esperado objeto")
        nome = etapa.get("nome")
        modelo = etapa.get("modelo")
        anexos = etapa.get("anexos")
        saida = etapa.get("saida")
        if not isinstance(nome, str) or not nome.strip():
            raise ValueError(f"Etapa {indice} inválida: 'nome' obrigatório")
        modelos: List[str] = []
        if isinstance(modelo, str) and modelo.strip():
            modelos.append(modelo.strip())
        if anexos is not None:
            if not isinstance(anexos, list) or not anexos:
                raise ValueError(f"Etapa {indice} inválida: 'anexos' deve ser lista não vazia")
            for item in anexos:
                if not isinstance(item, str) or not item.strip():
                    raise ValueError(f"Etapa {indice} inválida: item de 'anexos' deve ser string")
                modelos.append(item.strip())
        if not modelos:
            raise ValueError(f"Etapa {indice} inválida: informe 'modelo' ou 'anexos'")
        if saida is not None and not isinstance(saida, str):
            raise ValueError(f"Etapa {indice} inválida: 'saida' deve ser string")

        etapas.append(EtapaRito(nome=nome.strip(), modelos=tuple(modelos), saida=saida.strip() if isinstance(saida, str) else None))

    return etapas


def montar_trabalhos(modelos_dir: Path, modelos_padrao: List[Path], etapas_rito: List[EtapaRito] | None, etapa_alvo: str | None) -> List[TrabalhoGeracao]:
    if etapas_rito is None:
        trabalhos = [TrabalhoGeracao(nome_etapa=modelo.stem, caminho_modelo=modelo, nome_saida=modelo.name) for modelo in modelos_padrao]
    else:
        if etapa_alvo:
            etapa_encontrada = next((etapa for etapa in etapas_rito if etapa.nome == etapa_alvo), None)
            if etapa_encontrada is None:
                disponiveis = ", ".join(etapa.nome for etapa in etapas_rito)
                raise ValueError(f"Etapa '{etapa_alvo}' não encontrada. Etapas disponíveis: {disponiveis}")

            trabalhos_etapa: List[TrabalhoGeracao] = []
            for indice_modelo, nome_modelo in enumerate(etapa_encontrada.modelos):
                caminho_modelo = modelos_dir / nome_modelo
                if not caminho_modelo.exists():
                    raise FileNotFoundError(
                        f"Modelo da etapa '{etapa_encontrada.nome}' não encontrado: {caminho_modelo}. "
                        f"Inclua o arquivo para seguir o rito processual."
                    )
                if etapa_encontrada.saida and len(etapa_encontrada.modelos) == 1:
                    nome_saida = etapa_encontrada.saida
                else:
                    nome_saida = Path(nome_modelo).name
                nome_etapa = etapa_encontrada.nome if len(etapa_encontrada.modelos) == 1 else f"{etapa_encontrada.nome} ({indice_modelo + 1}/{len(etapa_encontrada.modelos)})"
                trabalhos_etapa.append(TrabalhoGeracao(nome_etapa=nome_etapa, caminho_modelo=caminho_modelo, nome_saida=nome_saida))
            return trabalhos_etapa

        trabalhos = []
        for etapa in etapas_rito:
            for indice_modelo, nome_modelo in enumerate(etapa.modelos):
                caminho_modelo = modelos_dir / nome_modelo
                if not caminho_modelo.exists():
                    raise FileNotFoundError(
                        f"Modelo da etapa '{etapa.nome}' não encontrado: {caminho_modelo}. "
                        f"Inclua o arquivo para seguir o rito processual."
                    )
                if etapa.saida and len(etapa.modelos) == 1:
                    nome_saida = etapa.saida
                else:
                    nome_saida = Path(nome_modelo).name
                nome_etapa = etapa.nome if len(etapa.modelos) == 1 else f"{etapa.nome} ({indice_modelo + 1}/{len(etapa.modelos)})"
                trabalhos.append(TrabalhoGeracao(nome_etapa=nome_etapa, caminho_modelo=caminho_modelo, nome_saida=nome_saida))

    if etapa_alvo:
        trabalhos_filtrados = [tr for tr in trabalhos if tr.nome_etapa == etapa_alvo]
        if not trabalhos_filtrados:
            disponiveis = ", ".join(tr.nome_etapa for tr in trabalhos)
            raise ValueError(f"Etapa '{etapa_alvo}' não encontrada. Etapas disponíveis: {disponiveis}")
        return trabalhos_filtrados

    return trabalhos


def descobrir_proxima_etapa(rito: Sequence[EtapaRito], pasta_modelos: Path) -> EtapaRito | None:
    for etapa in rito:
        if any(not (pasta_modelos / modelo).exists() for modelo in etapa.modelos):
            return etapa
    return None


def gerar_documentos(trabalhos: Iterable[TrabalhoGeracao], dados: Dict[str, object], pasta_saida: Path) -> None:
    pasta_saida.mkdir(parents=True, exist_ok=True)

    for trabalho in trabalhos:
        destino = pasta_saida / trabalho.nome_saida
        if trabalho.caminho_modelo.suffix.lower() in {".md", ".txt"}:
            conteudo = trabalho.caminho_modelo.read_text(encoding="utf-8")
            campos = extrair_campos(conteudo)
            validar_campos_obrigatorios(campos, dados, trabalho.caminho_modelo.name)

            documento = renderizar_modelo(conteudo, dados)
            destino.write_text(documento, encoding="utf-8")
        else:
            shutil.copy2(trabalho.caminho_modelo, destino)
        print(f"Gerado [{trabalho.nome_etapa}]: {destino}")


def exportar_inventario(modelos: Iterable[Path], destino: Path) -> None:
    inventario: Dict[str, List[str]] = {}
    for modelo in modelos:
        if modelo.suffix.lower() in {".md", ".txt"}:
            campos = extrair_campos(modelo.read_text(encoding="utf-8"))
            inventario[modelo.name] = campos

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(inventario, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Inventário exportado: {destino}")


def montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera peças documentais de licitação com fidelidade aos modelos.")
    parser.add_argument("--dados", type=Path, help="Arquivo JSON com os dados da licitação")
    parser.add_argument("--modelos", required=True, type=Path, help="Pasta com modelos Markdown")
    parser.add_argument("--saida", type=Path, help="Pasta de saída dos documentos gerados")
    parser.add_argument("--rito", type=Path, help="JSON com a sequência do rito processual e modelos por etapa")
    parser.add_argument("--etapa", type=str, help="Gera somente uma etapa específica do rito")
    parser.add_argument("--proxima-etapa", action="store_true", help="Mostra qual modelo falta para continuar o rito")
    parser.add_argument(
        "--inventario-placeholders",
        type=Path,
        help="Exporta um JSON com os placeholders de cada modelo e encerra",
    )
    return parser


def main() -> int:
    args = montar_parser().parse_args()

    modelos = listar_modelos(args.modelos)

    if args.inventario_placeholders:
        exportar_inventario(modelos, args.inventario_placeholders)
        return 0

    if args.proxima_etapa:
        if not args.rito:
            raise ValueError("Use --rito junto com --proxima-etapa")
        etapas_rito = carregar_rito(args.rito)
        proxima = descobrir_proxima_etapa(etapas_rito, args.modelos)
        if proxima:
            faltantes = [modelo for modelo in proxima.modelos if not (args.modelos / modelo).exists()]
            print(f"Próxima etapa pendente: {proxima.nome}")
            if len(faltantes) == 1:
                print(f"Envie o modelo para: {faltantes[0]}")
            else:
                print("Envie os modelos pendentes:")
                for arquivo in faltantes:
                    print(f"- {arquivo}")
        else:
            print("Todas as etapas do rito já possuem modelo cadastrado.")
        return 0

    if args.dados is None:
        raise ValueError("Informe --dados para gerar documentos")
    if args.saida is None:
        raise ValueError("Informe --saida para gerar documentos")

    dados = carregar_dados(args.dados)
    etapas_rito = carregar_rito(args.rito) if args.rito else None
    trabalhos = montar_trabalhos(args.modelos, modelos, etapas_rito, args.etapa)
    gerar_documentos(trabalhos, dados, args.saida)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
