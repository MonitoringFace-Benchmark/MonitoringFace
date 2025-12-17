#!/usr/bin/env python3
"""
Test script to validate CLI and YAML parsing without running full experiments
"""
import sys
import os

# Add Infrastructure to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from Infrastructure.Parser.YamlParser import YamlParser, ExperimentSuiteParser, YamlParserException


def test_yaml_parser():
    """Test parsing of example YAML files"""
    print("Testing YAML Parser...")
    print("=" * 60)
    
    example_files = [
        "Infrastructure/experiments/example_synthetic_experiment.yaml",
        "Infrastructure/experiments/example_patterns.yaml",
        "Infrastructure/experiments/example_case_study.yaml"
    ]
    
    for yaml_file in example_files:
        print(f"\nTesting: {yaml_file}")
        try:
            parser = YamlParser(yaml_file)
            experiment = parser.parse_experiment()
            
            print(f"  ✓ Successfully parsed")
            print(f"    - Experiment: {experiment['benchmark_contract'].experiment_name}")
            print(f"    - Type: {experiment['experiment_type'].name}")
            print(f"    - Tools: {', '.join(experiment['tools_to_build'])}")
            
        except YamlParserException as e:
            print(f"  ✗ Parser error: {e}")
            return False
        except Exception as e:
            print(f"  ✗ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True


def test_suite_parser():
    """Test parsing of experiment suite"""
    print("\n\nTesting Experiment Suite Parser...")
    print("=" * 60)
    
    suite_file = "Infrastructure/experiments/experiments_suite.yaml"
    
    print(f"\nTesting: {suite_file}")
    try:
        parser = ExperimentSuiteParser(suite_file)
        experiment_paths = parser.get_experiment_paths()
        
        print(f"  ✓ Successfully parsed suite")
        print(f"    - Found {len(experiment_paths)} enabled experiment(s)")
        for i, path in enumerate(experiment_paths, 1):
            print(f"      {i}. {os.path.basename(path)}")
        
        return True
        
    except YamlParserException as e:
        print(f"  ✗ Parser error: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cli_help():
    """Test CLI help message"""
    print("\n\nTesting CLI Help...")
    print("=" * 60)
    
    try:
        from Infrastructure.cli import CLI
        cli = CLI()
        
        print("\n  ✓ CLI module loaded successfully")
        print("\nTo see help message, run:")
        print("  python -m Infrastructure.main --help")
        
        return True
        
    except ImportError as e:
        print(f"  ✗ Import error: {e}")
        print("\nMake sure dependencies are installed:")
        print("  pip install -r Infrastructure/requirements.txt")
        return False
    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("MonitoringFace CLI Test Suite")
    print("=" * 60)
    
    tests = [
        ("YAML Parser", test_yaml_parser),
        ("Suite Parser", test_suite_parser),
        ("CLI Module", test_cli_help)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    all_passed = True
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n✓ All tests passed!")
        print("\nYou can now run experiments:")
        print("  python -m Infrastructure.main experiments/example_synthetic_experiment.yaml --dry-run")
        return 0
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
        print("\nCommon issues:")
        print("  - Missing dependencies: pip install -r Infrastructure/requirements.txt")
        print("  - YAML files not found: check that example files exist")
        return 1


if __name__ == "__main__":
    sys.exit(main())
