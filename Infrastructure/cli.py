"""
CLI module for MonitoringFace benchmark framework
Provides command-line interface for running experiments from YAML configuration files
"""
import argparse
import sys
import os
from typing import List, Any, AnyStr

from Infrastructure.DataLoader.Resolver import BenchmarkResolver, Location
from Infrastructure.Parser.YamlParser import YamlParser, ExperimentSuiteParser, YamlParserException
from Infrastructure.BenchmarkBuilder.BenchmarkBuilder import BenchmarkBuilder


class CLI:
    """Command-line interface for MonitoringFace"""
    
    def __init__(self, path_to_module: AnyStr):
        self.parser = self._create_parser()

        self.infra_folder = f"{path_to_module}/Infrastructure"
        self.build_folder = f"{self.infra_folder}/build"
        self.experiment_folder = f"{self.infra_folder}/experiments"

        self.archive_folder = f"{path_to_module}/Archive"
        self.benchmark_folder = f"{self.archive_folder}/Benchmarks"

        if not os.path.exists(self.build_folder):
            os.mkdir(self.build_folder)

        if not os.path.exists(self.experiment_folder):
            os.mkdir(self.experiment_folder)
    
    @staticmethod
    def _create_parser() -> argparse.ArgumentParser:
        """Create and configure argument parser"""
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
        
        return parser
    
    @staticmethod
    def _is_suite_config(config_path: str) -> bool:
        """
        Detect if config file is an experiment suite
        
        Args:
            config_path: Path to YAML configuration file
            
        Returns:
            True if config contains 'experiments' list, False otherwise
        """
        try:
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            return 'experiments' in config
        except Exception:
            return False
    
    def run_single_experiment(self, config_name: AnyStr, dry_run: bool = False, verbose: bool = False) -> Any:
        """
        Run a single experiment from YAML configuration
        
        Args:
            dry_run: If True, only validate without running
            verbose: Enable verbose output
            
        Returns:
            Experiment results or None if dry_run
        """
        yaml_file = f"{self.benchmark_folder}/{config_name}"

        if verbose:
            print(f"Loading experiment configuration from: {yaml_file}")
        
        try:
            # Parse configuration
            parser = YamlParser(yaml_path=yaml_file, path_to_build=self.build_folder, path_to_experiments=self.experiment_folder)
            experiment_config = parser.parse_experiment()
            
            if verbose:
                print(f"Experiment name: {experiment_config['benchmark_contract'].experiment_name}")
                print(f"Experiment type: {experiment_config['experiment_type'].name}")
                print(f"Tools to build: {', '.join(experiment_config['tools_to_build'])}")
            
            if dry_run:
                print(f"✓ Configuration validated successfully: {yaml_file}")
                return None
            
            # Create benchmark - note: parameter name is 'contract' not 'benchmark_contract'
            benchmark = BenchmarkBuilder(
                contract=experiment_config['benchmark_contract'],
                path_to_project=experiment_config['path_to_project'],
                data_setup=experiment_config['data_setup'],
                gen_mode=experiment_config['experiment_type'],
                time_guard=experiment_config['time_guarded'],
                tools_to_build=experiment_config['tools_to_build'],
                oracle=experiment_config['oracle']
            )
            
            # Get monitors to run
            monitors = experiment_config['monitor_manager'].get_monitors(
                experiment_config['tools_to_build']
            )
            
            if verbose:
                print(f"Running experiment with {len(monitors)} monitor(s)...")
            
            # Run benchmark
            results = benchmark.run(monitors, {})
            
            print(f"✓ Experiment completed: {experiment_config['benchmark_contract'].experiment_name}")
            if verbose:
                print(f"Results: {results}")
            
            return results
            
        except YamlParserException as e:
            print(f"✗ Configuration error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"✗ Error running experiment: {e}", file=sys.stderr)
            if verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)
    
    def run_experiment_suite(self, suite_path: str, dry_run: bool = False, verbose: bool = False) -> List[Any]:
        """
        Run multiple experiments from a suite configuration
        
        Args:
            suite_path: Path to experiment suite YAML file
            dry_run: If True, only validate without running
            verbose: Enable verbose output
            
        Returns:
            List of experiment results or empty list if dry_run
        """
        if verbose:
            print(f"Loading experiment suite from: {suite_path}")
        
        try:
            # Parse suite
            suite_parser = ExperimentSuiteParser(suite_path)
            experiment_paths = suite_parser.get_experiment_paths()
            
            print(f"Found {len(experiment_paths)} enabled experiment(s) in suite")
            
            if dry_run:
                # Validate all experiments
                for i, exp_path in enumerate(experiment_paths, 1):
                    if verbose:
                        print(f"\nValidating experiment {i}/{len(experiment_paths)}: {exp_path}")
                    self.run_single_experiment(exp_path, dry_run=True, verbose=verbose)
                print(f"\n✓ All {len(experiment_paths)} experiment(s) validated successfully")
                return []
            
            # Run all experiments
            results = []
            for i, exp_path in enumerate(experiment_paths, 1):
                print(f"\n{'='*60}")
                print(f"Running experiment {i}/{len(experiment_paths)}: {os.path.basename(exp_path)}")
                print(f"{'='*60}")
                
                result = self.run_single_experiment(exp_path, dry_run=False, verbose=verbose)
                results.append(result)
            
            print(f"\n{'='*60}")
            print(f"✓ All {len(experiment_paths)} experiment(s) completed successfully")
            print(f"{'='*60}")
            
            return results
            
        except YamlParserException as e:
            print(f"✗ Suite configuration error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"✗ Error running experiment suite: {e}", file=sys.stderr)
            if verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)
    
    def run(self, argv: List[str] = None):
        """
        Main entry point for CLI
        
        Args:
            argv: Command-line arguments (defaults to sys.argv)
        """
        args = self.parser.parse_args(argv)

        br = BenchmarkResolver(name=args.config, path_to_infra=self.infra_folder, path_to_archive=self.archive_folder)
        location = br.resolve()
        if location == Location.Unavailable:
            raise ValueError(f"The configuration File {args.config} is unavailable local and remote")
        elif location == Location.Remote:
            br.get_remote_config(path_to_archive_benchmark=self.benchmark_folder, name=args.config)

        # Detect if suite or single experiment
        is_suite = args.suite or self._is_suite_config(f"{self.benchmark_folder}/{args.config}")
        
        if is_suite:
            if args.verbose:
                print("Detected experiment suite configuration")
            self.run_experiment_suite(
                suite_path=args.config,
                dry_run=args.dry_run,
                verbose=args.verbose
            )
        else:
            if args.verbose:
                print("Detected single experiment configuration")
            self.run_single_experiment(
                config_name=args.config,
                dry_run=args.dry_run,
                verbose=args.verbose
            )


def main(argv: List[str] = None, path_to_module: AnyStr = None):
    """Main entry point for command-line execution"""
    cli = CLI(path_to_module=path_to_module)
    cli.run(argv)
