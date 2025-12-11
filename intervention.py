#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple
from urllib.parse import urlparse

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()


def ensure_repositories(dict_path: str, nuclei_templates_path: str):
    """Vérifie et clone les répertoires nécessaires s'ils n'existent pas"""
    dict_dir = Path(dict_path)
    nuclei_dir = Path(nuclei_templates_path)
    
    if dict_dir.exists() and any(dict_dir.glob("*.txt")):
        console.print(f"[green]✓[/green] OneListForAll trouvé")
    else:
        console.print(f"[cyan]📥[/cyan] Clonage de OneListForAll...")
        try:
            parent_dir = dict_dir.parent
            
            if parent_dir.name == "OneListForAll":
                one_list_dir = parent_dir
            else:
                one_list_dir = parent_dir / "OneListForAll"
            
            if not parent_dir.exists():
                parent_dir.mkdir(parents=True, exist_ok=True)
            
            if one_list_dir.exists():
                import shutil
                shutil.rmtree(one_list_dir)
            
            subprocess.run(
                ["git", "clone", "https://github.com/six2dez/OneListForAll.git", str(one_list_dir)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            console.print(f"[green]✓[/green] OneListForAll cloné avec succès")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Erreur lors du clonage de OneListForAll[/red]")
            if e.stderr:
                console.print(f"[red]Détails: {e.stderr.decode()}[/red]")
            sys.exit(1)
        except FileNotFoundError:
            console.print("[red]Erreur: git n'est pas installé ou n'est pas dans le PATH[/red]")
            sys.exit(1)
    
    if nuclei_dir.exists() and any(nuclei_dir.rglob("*.yaml")):
        console.print(f"[green]✓[/green] nuclei-templates trouvé")
    else:
        console.print(f"[cyan]📥[/cyan] Clonage de nuclei-templates...")
        try:
            parent_dir = nuclei_dir.parent
            if not parent_dir.exists():
                parent_dir.mkdir(parents=True, exist_ok=True)
            
            if nuclei_dir.exists():
                import shutil
                shutil.rmtree(nuclei_dir)
            
            subprocess.run(
                ["git", "clone", "https://github.com/projectdiscovery/nuclei-templates.git", str(nuclei_dir)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            console.print(f"[green]✓[/green] nuclei-templates cloné avec succès")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Erreur lors du clonage de nuclei-templates[/red]")
            if e.stderr:
                console.print(f"[red]Détails: {e.stderr.decode()}[/red]")
            sys.exit(1)
        except FileNotFoundError:
            console.print("[red]Erreur: git n'est pas installé ou n'est pas dans le PATH[/red]")
            sys.exit(1)


class Intervention:
    def __init__(self, dict_path: str, nuclei_templates_path: str, mode: str = "long", 
                 occurrence: int = 10, verbose: bool = False):
        self.dict_path = Path(dict_path)
        self.nuclei_templates_path = Path(nuclei_templates_path)
        self.mode = mode
        self.occurrence = occurrence
        self.verbose = verbose
        self.tech_to_dict = {}
        self.detected_techs = defaultdict(set)
        self.ffuf_results = {}
        
        self._load_technologies()
    
    def _load_technologies(self):
        """Charge la liste des technologies disponibles depuis les dictionnaires"""
        if not self.dict_path.exists():
            console.print(f"[red]Erreur: Le répertoire {self.dict_path} n'existe pas[/red]")
            sys.exit(1)
        
        pattern = re.compile(r'^(.+?)_(short|long)\.txt$')
        techs = set()
        
        for file in self.dict_path.glob("*.txt"):
            match = pattern.match(file.name)
            if match:
                tech_name = match.group(1)
                dict_type = match.group(2)
                techs.add(tech_name)
                
                if tech_name not in self.tech_to_dict:
                    self.tech_to_dict[tech_name] = {}
                
                if dict_type == self.mode or (dict_type == "long" and self.mode == "long"):
                    self.tech_to_dict[tech_name][dict_type] = str(file)
        
        if self.verbose:
            console.print(f"[green]✓[/green] {len(techs)} technologies trouvées dans les dictionnaires")
    
    def _normalize_tech_name(self, tech_name: str) -> str:
        """Normalise le nom de la techno pour correspondre aux dictionnaires"""
        tech_name = tech_name.lower()
        tech_name = tech_name.replace(" ", "-")
        tech_name = tech_name.replace("_", "-")
        tech_name = tech_name.replace(".", "")
        tech_name = tech_name.replace("detect", "")
        tech_name = tech_name.replace("detection", "")
        tech_name = tech_name.replace("-detect", "")
        tech_name = tech_name.replace("-detection", "")
        tech_name = tech_name.strip("-")
        return tech_name
    
    def _find_matching_dict(self, tech_name: str) -> str:
        """Trouve le dictionnaire correspondant à une techno"""
        normalized = self._normalize_tech_name(tech_name)
        
        if normalized in self.tech_to_dict:
            if self.mode in self.tech_to_dict[normalized]:
                return self.tech_to_dict[normalized][self.mode]
            elif "long" in self.tech_to_dict[normalized]:
                return self.tech_to_dict[normalized]["long"]
            elif "short" in self.tech_to_dict[normalized]:
                return self.tech_to_dict[normalized]["short"]
        
        for tech in self.tech_to_dict.keys():
            if normalized == tech:
                if self.mode in self.tech_to_dict[tech]:
                    return self.tech_to_dict[tech][self.mode]
                elif "long" in self.tech_to_dict[tech]:
                    return self.tech_to_dict[tech]["long"]
                elif "short" in self.tech_to_dict[tech]:
                    return self.tech_to_dict[tech]["short"]
            elif normalized in tech or tech in normalized:
                if self.mode in self.tech_to_dict[tech]:
                    return self.tech_to_dict[tech][self.mode]
                elif "long" in self.tech_to_dict[tech]:
                    return self.tech_to_dict[tech]["long"]
                elif "short" in self.tech_to_dict[tech]:
                    return self.tech_to_dict[tech]["short"]
        
        return None
    
    def detect_technologies(self, url: str) -> Set[str]:
        """Détecte les technologies avec nuclei"""
        detected = set()
        
        tech_detect_path = self.nuclei_templates_path / "http/technologies/tech-detect.yaml"
        favicon_path = self.nuclei_templates_path / "http/technologies/favicon-detect.yaml"
        exposures_path = ""
        exposed_panels_path = ""
        
        templates_to_use = []
        if tech_detect_path.exists():
            templates_to_use.extend(["-t", str(tech_detect_path)])
            if self.verbose:
                console.print(f"  [dim]Template trouvé: {tech_detect_path}[/dim]")
        if favicon_path.exists():
            templates_to_use.extend(["-t", str(favicon_path)])
            if self.verbose:
                console.print(f"  [dim]Template trouvé: {favicon_path}[/dim]")
        if exposures_path.exists():
            templates_to_use.extend(["-t", str(exposures_path)])
            if self.verbose:
                console.print(f"  [dim]Dossier trouvé: {exposures_path}[/dim]")
        if exposed_panels_path.exists():
            templates_to_use.extend(["-t", str(exposed_panels_path)])
            if self.verbose:
                console.print(f"  [dim]Dossier trouvé: {exposed_panels_path}[/dim]")
        
        if not templates_to_use:
            console.print("[yellow]⚠[/yellow] Aucun template nuclei trouvé")
            if self.verbose:
                console.print(f"  [dim]Recherche dans: {self.nuclei_templates_path}[/dim]")
            return detected
        
        cmd = [
            "nuclei",
            "-u", url,
        ] + templates_to_use + [
            "-j"
        ]
        
        try:
            if self.verbose:
                console.print(f"[cyan]🔍[/cyan] Détection des technologies pour {url}")
                console.print(f"  [dim]Commande: {' '.join(cmd)}[/dim]")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                if self.verbose:
                    console.print(f"[yellow]⚠[/yellow] nuclei a retourné le code {result.returncode}")
                    if result.stderr:
                        console.print(f"[yellow]Erreur: {result.stderr}[/yellow]")
                else:
                    console.print(f"[yellow]⚠[/yellow] Erreur lors de la détection")
            
            if result.stdout:
                for line in result.stdout.splitlines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        tech_name = None
                        
                        if "matcher-name" in data:
                            tech_name = data["matcher-name"]
                        elif "info" in data:
                            if "name" in data["info"]:
                                tech_name = data["info"]["name"]
                            elif "tags" in data["info"]:
                                tags = data["info"]["tags"]
                                if isinstance(tags, list) and tags:
                                    tech_name = tags[0]
                        
                        if tech_name:
                            tech_name = self._normalize_tech_name(tech_name)
                            detected.add(tech_name)
                            if self.verbose:
                                console.print(f"  [green]✓[/green] {tech_name}")
                    except json.JSONDecodeError:
                        if self.verbose:
                            console.print(f"  [dim]Ligne non-JSON ignorée: {line[:50]}...[/dim]")
                        continue
            
            if self.verbose:
                if result.stderr:
                    console.print(f"  [dim]stderr: {result.stderr[:200]}...[/dim]" if len(result.stderr) > 200 else f"  [dim]stderr: {result.stderr}[/dim]")
                console.print(f"  [dim]Code de retour: {result.returncode}[/dim]")
                console.print(f"  [dim]Lignes de sortie: {len(result.stdout.splitlines())}[/dim]")
                if not detected:
                    console.print(f"  [yellow]⚠[/yellow] Aucune sortie de nuclei (stdout vide)")
            
        except subprocess.TimeoutExpired:
            console.print(f"[yellow]⚠[/yellow] Timeout lors de la détection pour {url}")
        except FileNotFoundError:
            console.print("[red]Erreur: nuclei n'est pas installé ou n'est pas dans le PATH[/red]")
            console.print("[yellow]Installez nuclei: https://github.com/projectdiscovery/nuclei#installation[/yellow]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Erreur lors de la détection: {e}[/red]")
            if self.verbose:
                import traceback
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
        
        return detected
    
    def run_ffuf(self, url: str, wordlist: str, tech_name: str) -> List[Dict]:
        """Lance ffuf avec un dictionnaire"""
        results = []
        
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        output_file = f"/tmp/ffuf_{tech_name}_{hash(url)}.json"
        
        cmd = [
            "ffuf",
            "-u", f"{base_url}/FUZZ",
            "-w", wordlist,
            "-o", output_file,
            "-of", "json",
            "-mc", "200,201,202,204,301,302,307,401,403",
            "-t", "50",
            "-s"
        ]
        
        try:
            if self.verbose:
                console.print(f"  [cyan]🚀[/cyan] Lancement ffuf avec {tech_name} ({self.mode})")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600
            )
            
            if os.path.exists(output_file):
                with open(output_file, 'r') as f:
                    ffuf_data = json.load(f)
                    if "results" in ffuf_data:
                        results = ffuf_data["results"]
                
                os.remove(output_file)
            
        except subprocess.TimeoutExpired:
            console.print(f"[yellow]⚠[/yellow] Timeout lors de ffuf pour {tech_name}")
        except FileNotFoundError:
            console.print("[red]Erreur: ffuf n'est pas installé ou n'est pas dans le PATH[/red]")
            sys.exit(1)
        except Exception as e:
            if self.verbose:
                console.print(f"[red]Erreur lors de ffuf: {e}[/red]")
        
        return results
    
    def analyze_results(self, results: List[Dict]) -> List[Dict]:
        """Analyse les résultats par longueur et occurrence"""
        length_counts = defaultdict(int)
        
        for result in results:
            length = result.get("length", 0)
            length_counts[length] += 1
        
        interesting_results = []
        for result in results:
            length = result.get("length", 0)
            count = length_counts[length]
            
            if count <= self.occurrence:
                interesting_results.append({
                    **result,
                    "occurrence_count": count
                })
        
        return interesting_results
    
    def process_url(self, url: str):
        """Traite une URL complète"""
        console.print(f"\n[bold blue]📋 Traitement de {url}[/bold blue]")
        
        detected_techs = self.detect_technologies(url)
        self.detected_techs[url] = detected_techs
        
        if not detected_techs:
            console.print(f"[yellow]⚠[/yellow] Aucune technologie détectée pour {url}")
            return
        
        console.print(f"[green]✓[/green] {len(detected_techs)} technologie(s) détectée(s)")
        
        all_results = []
        tech_results_map = {}
        
        for tech in detected_techs:
            dict_path = self._find_matching_dict(tech)
            
            if not dict_path:
                if self.verbose:
                    console.print(f"  [yellow]⚠[/yellow] Pas de dictionnaire trouvé pour {tech}")
                continue
            
            if self.verbose:
                console.print(f"  [cyan]📚[/cyan] Dictionnaire trouvé pour {tech}: {Path(dict_path).name}")
            
            results = self.run_ffuf(url, dict_path, tech)
            
            if results:
                analyzed = self.analyze_results(results)
                if analyzed:
                    for result in analyzed:
                        result["tech"] = tech
                        result["dict_used"] = Path(dict_path).name
                    all_results.extend(analyzed)
                    tech_results_map[tech] = analyzed
                    self.ffuf_results[f"{url}_{tech}"] = analyzed
                    
                    if self.verbose:
                        console.print(f"  [green]✓[/green] {len(analyzed)} résultat(s) intéressant(s) pour {tech}")
        
        if all_results:
            self._save_results(url, all_results, tech_results_map)
            self._display_results(url, all_results, tech_results_map)
        else:
            console.print(f"[yellow]⚠[/yellow] Aucun résultat intéressant trouvé pour {url}")
    
    def _save_results(self, url: str, results: List[Dict], tech_results_map: Dict[str, List[Dict]]):
        """Sauvegarde les résultats en JSON"""
        safe_url = url.replace("://", "_").replace("/", "_").replace(":", "_")
        output_file = f"intervention_results_{safe_url}.json"
        
        with open(output_file, 'w') as f:
            json.dump({
                "url": url,
                "mode": self.mode,
                "occurrence_threshold": self.occurrence,
                "technologies_detected": list(tech_results_map.keys()),
                "results_by_tech": {
                    tech: len(results_list) 
                    for tech, results_list in tech_results_map.items()
                },
                "results": results
            }, f, indent=2)
        
        console.print(f"[green]✓[/green] Résultats sauvegardés dans {output_file}")
    
    def _display_results(self, url: str, results: List[Dict], tech_results_map: Dict[str, List[Dict]]):
        """Affiche les résultats avec Rich"""
        if not results:
            return
        
        if len(tech_results_map) > 1:
            console.print(f"\n[bold cyan]📊 Résultats par technologie:[/bold cyan]")
            for tech, tech_results in tech_results_map.items():
                console.print(f"  • {tech}: {len(tech_results)} résultat(s)")
        
        table = Table(title=f"Résultats intéressants pour {url} (≤{self.occurrence} occurrences)")
        table.add_column("URL", style="cyan", no_wrap=False)
        table.add_column("Techno", style="blue", justify="left")
        table.add_column("Status", style="green", justify="center")
        table.add_column("Taille", style="yellow", justify="right")
        table.add_column("Occurrences", style="magenta", justify="center")
        
        for result in sorted(results, key=lambda x: (x.get("occurrence_count", 0), x.get("length", 0))):
            url_path = result.get("url", "")
            tech = result.get("tech", "N/A")
            status = str(result.get("status", ""))
            length = str(result.get("length", ""))
            occ = str(result.get("occurrence_count", ""))
            
            table.add_row(url_path, tech, status, length, occ)
        
        console.print(table)
        console.print(f"[green]✓[/green] {len(results)} résultat(s) intéressant(s) trouvé(s) sur {len(tech_results_map)} technologie(s)")
    
    def run(self, urls: List[str]):
        """Lance l'intervention sur les URLs"""
        console.print(Panel.fit(
            f"[bold]Intervention[/bold]\n"
            f"Mode: {self.mode}\n"
            f"Seuil d'occurrence: {self.occurrence}\n"
            f"URLs: {len(urls)}",
            title="Configuration"
        ))
        
        for url in urls:
            self.process_url(url)
        
        console.print("\n[bold green]✓ Intervention terminée[/bold green]")


def main():
    parser = argparse.ArgumentParser(
        description="Outil d'intervention intelligent pour fuzzing avec ffuf basé sur les technologies détectées"
    )
    parser.add_argument(
        "urls",
        nargs="+",
        help="URL(s) ou fichier contenant les URLs à traiter"
    )
    parser.add_argument(
        "--dict",
        default="OneListForAll/dict",
        help="Chemin vers le répertoire des dictionnaires (défaut: OneListForAll/dict)"
    )
    parser.add_argument(
        "--nuclei-templates",
        default="nuclei-templates",
        help="Chemin vers les templates nuclei (défaut: nuclei-templates)"
    )
    parser.add_argument(
        "--mode",
        choices=["short", "long"],
        default="long",
        help="Mode de dictionnaire à utiliser (défaut: long)"
    )
    parser.add_argument(
        "--occurrence",
        type=int,
        default=10,
        help="Nombre maximum d'occurrences pour considérer un résultat intéressant (défaut: 10)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Mode verbose pour plus de détails"
    )
    parser.add_argument(
        "--no-auto-clone",
        action="store_true",
        help="Désactive le clonage automatique des répertoires"
    )
    
    args = parser.parse_args()
    
    if not args.no_auto_clone:
        ensure_repositories(args.dict, args.nuclei_templates)
    
    urls = []
    for url_arg in args.urls:
        if os.path.isfile(url_arg):
            with open(url_arg, 'r') as f:
                urls.extend([line.strip() for line in f if line.strip()])
        else:
            urls.append(url_arg)
    
    intervention = Intervention(
        dict_path=args.dict,
        nuclei_templates_path=args.nuclei_templates,
        mode=args.mode,
        occurrence=args.occurrence,
        verbose=args.verbose
    )
    
    intervention.run(urls)


if __name__ == "__main__":
    main()


