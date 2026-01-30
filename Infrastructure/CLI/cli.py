"""
CLI module for MonitoringFace benchmark framework
Provides command-line interface for running experiments from YAML configuration files
"""
import argparse
import shutil
import sys
import os
from datetime import datetime
from typing import List, Any, AnyStr

from Infrastructure.DataLoader.Resolver import BenchmarkResolver, Location
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.Parser.YamlParser import YamlParser, ExperimentSuiteParser, YamlParserException
from Infrastructure.BenchmarkBuilder.BenchmarkBuilder import BenchmarkBuilder
from Infrastructure.constants import LENGTH


class CLI:
    """Command-line interface for MonitoringFace"""
    
    def __init__(self, path_to_module: AnyStr):
        self.parser = self._create_parser()

        self.path_manager = PathManager()
        self.path_to_module = path_to_module
        self.infra_folder = f"{self.path_to_module}/Infrastructure"
        self.build_folder = f"{self.infra_folder}/build"
        self.experiment_folder = f"{self.infra_folder}/experiments"

        self.archive_folder = f"{self.path_to_module}/Archive"
        self.benchmark_folder = f"{self.archive_folder}/Benchmarks"

        self.result_base_folder = f"{self.infra_folder}/results"

        self.path_manager.add_path("path_to_project", self.path_to_module)
        self.path_manager.add_path("path_to_build", self.build_folder)
        self.path_manager.add_path("path_to_experiments", self.experiment_folder)
        self.path_manager.add_path("path_to_archive", self.archive_folder)
        self.path_manager.add_path("path_to_benchmark", self.benchmark_folder)
        self.path_manager.add_path("path_to_results", self.result_base_folder)

        os.makedirs(self.result_base_folder, exist_ok=True)

        os.makedirs(self.build_folder, exist_ok=True)
        os.makedirs(self.experiment_folder, exist_ok=True)
    
    def _create_timestamped_result_folder(self, experiment_name: str) -> str:
        """Create a timestamped result folder for the current run."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_folder = os.path.join(self.result_base_folder, f"{experiment_name}_{timestamp}")
        os.makedirs(result_folder, exist_ok=True)
        return result_folder

    def _clean_all(self):
        shutil.rmtree(self.result_base_folder, ignore_errors=True)
        os.makedirs(self.result_base_folder, exist_ok=True)

    @staticmethod
    def _create_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog='MonitoringFace',
            description='MonitoringFace Benchmark Framework - Run monitoring experiments from YAML configurations',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Run a single experiment
  python -m Infrastructure.main experiments/my_experiment.yaml
  
  # Run a suite of experiments
  python -m Infrastructure.main experiments/experiments_suite.yaml
  
  # Dry run to validate configuration without execution
  python -m Infrastructure.main experiments/my_experiment.yaml --dry-run
            """
        )
        
        parser.add_argument(
            'config',
            type=str,
            help='Name of a YAML configuration file (single experiment or experiment suite)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate configuration without running experiments'
        )
        
        parser.add_argument(
            '--verbose',
            '-v',
            action='store_true',
            help='Enable verbose output'
        )
        
        parser.add_argument(
            '--suite',
            action='store_true',
            help='Force treat config as experiment suite (auto-detected by default)'
        )
        
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug mode - preserves scratch folder data for each tool execution'
        )

        parser.add_argument(
            '--no-measure',
            action='store_true',
            help='Disable the use of usr/bin/time measurement inside containers'
        )

        parser.add_argument(
            '--clean',
            action='store_true',
            help='Only retain the lastest result of an experiment'
        )

        parser.add_argument(
            '--clean-all',
            action='store_true',
            help='Force the clean-up of the entire results folder'
        )

        return parser

    def run(self, argv: List[str] = None):
        args = self.parser.parse_args(argv)

        cli_args = CLIArgs(
            debug=args.debug,
            verbose=args.verbose,
            measure=(False if args.no_measure else True),
            clean=args.clean,
            clean_all=args.clean_all
        )

        config_name = args.config.removeprefix(self.benchmark_folder)
        br = BenchmarkResolver(name=config_name, path_to_infra=self.infra_folder, path_to_archive=self.archive_folder)
        location = br.resolve()
        if location == Location.Unavailable:
            raise ValueError(f"The configuration File {config_name} is unavailable local and remote")
        elif location == Location.Remote:
            br.get_remote_config(path_to_archive_benchmark=self.benchmark_folder, name=config_name)

        is_suite = args.suite or self._is_suite_config(f"{self.benchmark_folder}/{config_name}")
        os.makedirs(self.result_base_folder, exist_ok=True)

        if is_suite:
            if args.verbose:
                print("Detected experiment suite configuration")
            self.run_experiment_suite(
                suite_name=config_name,
                cli_args=cli_args,
                dry_run=args.dry_run
            )
        else:
            if args.verbose:
                print("Detected single experiment configuration")
            self.run_single_experiment(
                config_name=config_name,
                dry_run=args.dry_run,
                cli_args=cli_args
            )

    @staticmethod
    def _is_suite_config(config_path: str) -> bool:
        try:
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            return 'experiments' in config
        except Exception():
            return False
    
    def run_single_experiment(self, config_name: AnyStr, cli_args: CLIArgs, dry_run: bool = False, result_folder: str = None, is_suite: bool = False) -> Any:
        yaml_file = f"{self.benchmark_folder}/{config_name}"

        if cli_args.verbose:
            print(f"Loading experiment configuration from: {yaml_file}")
        
        if cli_args.debug:
            print(f"Debug mode enabled - scratch folder data will be preserved")

        try:
            # Parse configuration
            parser = YamlParser(yaml_path=yaml_file, path_to_build=self.build_folder, path_to_experiments=self.experiment_folder)
            experiment_config = parser.parse_experiment(cli_args=cli_args)
            
            if cli_args.verbose:
                print(f"Experiment name: {experiment_config['benchmark_contract'].experiment_name}")
                print(f"Experiment type: {experiment_config['experiment_type'].name}")
                print(f"Tools to build: {', '.join(experiment_config['tools_to_build'])}")
            
            if dry_run:
                print(f"✓ Configuration validated successfully: {yaml_file}")
                return None

            benchmark = BenchmarkBuilder(
                contract=experiment_config['benchmark_contract'],
                path_manager=self.path_manager,
                data_setup=experiment_config['data_setup'],
                gen_mode=experiment_config['experiment_type'],
                time_guard=experiment_config['time_guarded'],
                tools_to_build=experiment_config['tools_to_build'],
                oracle=experiment_config['oracle'],
                seeds=experiment_config['seeds'],
                repeat_runs=experiment_config['repeat_experiments'],
                cli_args=cli_args
            )
            
            # Get monitors to run
            monitors = experiment_config['monitor_manager'].get_monitors(
                experiment_config['tools_to_build']
            )
            
            if cli_args.verbose:
                print(f"Running experiment with {len(monitors)} monitor(s)...")
            
            # Run benchmark
            results = benchmark.run(monitors)
            experiment_name = os.path.splitext(os.path.basename(yaml_file))[0]

            if not is_suite:
                if cli_args.clean_all:
                    self._clean_all()
                elif cli_args.clean:
                    for folder in os.listdir(self.result_base_folder):
                        if folder.startswith(experiment_name):
                            shutil.rmtree(os.path.join(self.result_base_folder, folder), ignore_errors=True)

            if result_folder is None:
                result_folder = self._create_timestamped_result_folder(experiment_name)

            results.to_csv(result_folder, experiment_name)

            print(f"✓ Experiment completed: {experiment_config['benchmark_contract'].experiment_name}")
            print(f"  Results saved to: {result_folder}")
            if cli_args.verbose:
                print(f"Results: {results}")
            
            return results
            
        except YamlParserException as e:
            print(f"✗ Configuration error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"✗ Error running experiment: {e}", file=sys.stderr)
            if cli_args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)
    
    def run_experiment_suite(self, suite_name: str, cli_args: CLIArgs, dry_run: bool = False) -> List[Any]:
        if cli_args.verbose:
            print(f"Loading experiment suite from: {suite_name}")
        
        if cli_args.debug:
            print(f"Debug mode enabled - scratch folder data will be preserved")

        try:
            suite_parser = ExperimentSuiteParser(self.path_to_module, suite_name)
            experiment_paths = suite_parser.get_experiment_paths()
            
            print(f"Found {len(experiment_paths)} enabled experiment(s) in suite")
            
            if dry_run:
                # Validate all experiments
                for i, exp_path in enumerate(experiment_paths, 1):
                    if cli_args.verbose:
                        print(f"\nValidating experiment {i}/{len(experiment_paths)}: {exp_path}")
                    self.run_single_experiment(exp_path, dry_run=True, cli_args=cli_args)
                print(f"\n✓ All {len(experiment_paths)} experiment(s) validated successfully")
                return []
            
            # Create a single timestamped folder for the entire suite
            suite_name_clean = os.path.splitext(os.path.basename(suite_name))[0]
            suite_result_folder = self._create_timestamped_result_folder(suite_name_clean)
            print(f"Suite results will be saved to: {suite_result_folder}")

            if cli_args.clean_all:
                self._clean_all()
            elif cli_args.clean:
                for folder in os.listdir(self.result_base_folder):
                    if folder.startswith(suite_name_clean):
                        shutil.rmtree(os.path.join(self.result_base_folder, folder), ignore_errors=True)

            # Run all experiments
            results = []
            for i, exp_path in enumerate(experiment_paths, 1):
                print(f"\n{'='*LENGTH}")
                print(f"Running experiment {i}/{len(experiment_paths)}: {os.path.basename(exp_path)}")
                print(f"{'='*LENGTH}")
                
                # Create a subfolder for each experiment within the suite folder
                exp_name = os.path.splitext(os.path.basename(exp_path))[0]
                exp_result_folder = os.path.join(suite_result_folder, exp_name)
                os.makedirs(exp_result_folder, exist_ok=True)

                result = self.run_single_experiment(
                    exp_path, cli_args=cli_args, dry_run=False,
                    is_suite=True, result_folder=exp_result_folder
                )
                results.append(result)

            print(f"\n{'='*LENGTH}")
            print(f"✓ All {len(experiment_paths)} experiment(s) completed successfully")
            print(f"{'='*LENGTH}")
            
            return results
            
        except YamlParserException as e:
            print(f"✗ Suite configuration error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"✗ Error running experiment suite: {e}", file=sys.stderr)
            if cli_args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)


def main(argv: List[str] = None, path_to_module: AnyStr = None):
    """Main entry point for command-line execution"""
    cli = CLI(path_to_module=path_to_module)
    cli.run(argv)
