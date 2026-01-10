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
from Infrastructure.constants import LENGTH


class CLI:
    """Command-line interface for MonitoringFace"""
    
    def __init__(self, path_to_module: AnyStr):
        self.parser = self._create_parser()

        self.path_to_module = path_to_module
        self.infra_folder = f"{self.path_to_module}/Infrastructure"
        self.build_folder = f"{self.infra_folder}/build"
        self.experiment_folder = f"{self.infra_folder}/experiments"

        self.archive_folder = f"{self.path_to_module}/Archive"
        self.benchmark_folder = f"{self.archive_folder}/Benchmarks"

        self.result_folder = f"{self.infra_folder}/results"
        os.makedirs(self.result_folder, exist_ok=True)

        os.makedirs(self.build_folder, exist_ok=True)
        os.makedirs(self.experiment_folder, exist_ok=True)
    
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
        
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug mode - preserves scratch folder data for each tool execution'
        )

        return parser
    
    @staticmethod
    def _is_suite_config(config_path: str) -> bool:
        try:
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            return 'experiments' in config
        except Exception():
            return False
    
    def run_single_experiment(self, config_name: AnyStr, dry_run: bool = False, verbose: bool = False, debug: bool = False) -> Any:
        yaml_file = f"{self.benchmark_folder}/{config_name}"

        if verbose:
            print(f"Loading experiment configuration from: {yaml_file}")
        
        if debug:
            print(f"Debug mode enabled - scratch folder data will be preserved")

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
                oracle=experiment_config['oracle'],
                seeds=experiment_config['seeds'],
                debug_mode=debug
            )
            
            # Get monitors to run
            monitors = experiment_config['monitor_manager'].get_monitors(
                experiment_config['tools_to_build']
            )
            
            if verbose:
                print(f"Running experiment with {len(monitors)} monitor(s)...")
            
            # Run benchmark
            results = benchmark.run(monitors, {})
            experiment_name = os.path.splitext(os.path.basename(yaml_file))[0]
            results.to_csv(self.result_folder, experiment_name)

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
    
    def run_experiment_suite(self, suite_name: str, dry_run: bool = False, verbose: bool = False, debug: bool = False) -> List[Any]:
        """
        Run multiple experiments from a suite configuration
        
        Args:
            suite_name: Path to experiment suite YAML file
            dry_run: If True, only validate without running
            verbose: Enable verbose output
            debug: Enable debug mode - preserves scratch folder data

        Returns:
            List of experiment results or empty list if dry_run
        """
        if verbose:
            print(f"Loading experiment suite from: {suite_name}")
        
        if debug:
            print(f"Debug mode enabled - scratch folder data will be preserved")

        try:
            suite_parser = ExperimentSuiteParser(self.path_to_module, suite_name)
            experiment_paths = suite_parser.get_experiment_paths()
            
            print(f"Found {len(experiment_paths)} enabled experiment(s) in suite")
            
            if dry_run:
                # Validate all experiments
                for i, exp_path in enumerate(experiment_paths, 1):
                    if verbose:
                        print(f"\nValidating experiment {i}/{len(experiment_paths)}: {exp_path}")
                    self.run_single_experiment(exp_path, dry_run=True, verbose=verbose, debug=debug)
                print(f"\n✓ All {len(experiment_paths)} experiment(s) validated successfully")
                return []
            
            # Run all experiments
            results = []
            for i, exp_path in enumerate(experiment_paths, 1):
                print(f"\n{'='*LENGTH}")
                print(f"Running experiment {i}/{len(experiment_paths)}: {os.path.basename(exp_path)}")
                print(f"{'='*LENGTH}")
                
                result = self.run_single_experiment(exp_path, dry_run=False, verbose=verbose, debug=debug)
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
                suite_name=args.config,
                dry_run=args.dry_run,
                verbose=args.verbose,
                debug=args.debug
            )
        else:
            if args.verbose:
                print("Detected single experiment configuration")
            self.run_single_experiment(
                config_name=args.config,
                dry_run=args.dry_run,
                verbose=args.verbose,
                debug=args.debug
            )


def main(argv: List[str] = None, path_to_module: AnyStr = None):
    """Main entry point for command-line execution"""
    cli = CLI(path_to_module=path_to_module)
    cli.run(argv)
