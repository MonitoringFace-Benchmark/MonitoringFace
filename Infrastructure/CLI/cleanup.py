"""
Cleanup module for MonitoringFace benchmark framework
Provides functionality to clean up accumulated results and experiment data
"""
import os
import shutil
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Tuple


class CleanupManager:
    """Manages cleanup of experiment results and data"""
    
    def __init__(self, result_base_folder: str, experiment_folder: str, verbose: bool = False):
        """
        Initialize cleanup manager
        
        Args:
            result_base_folder: Base folder for results (e.g., Infrastructure/results)
            experiment_folder: Folder for experiment data (e.g., Infrastructure/experiments)
            verbose: Enable verbose output
        """
        self.result_base_folder = result_base_folder
        self.experiment_folder = experiment_folder
        self.verbose = verbose
    
    def _parse_result_folder(self, folder_name: str) -> Tuple[str, datetime]:
        """
        Parse a result folder name into experiment name and timestamp
        
        Args:
            folder_name: Folder name like 'experiment_20240101_120000'
        
        Returns:
            Tuple of (experiment_name, timestamp)
        """
        # Split by last underscore to separate timestamp
        parts = folder_name.rsplit('_', 2)
        if len(parts) >= 3:
            experiment_name = parts[0]
            timestamp_str = f"{parts[1]}_{parts[2]}"
            try:
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                return experiment_name, timestamp
            except ValueError:
                # If parsing fails, use current time as fallback to avoid grouping issues
                if self.verbose:
                    print(f"Warning: Could not parse timestamp from folder name: {folder_name}")
                return folder_name, datetime.now()
        return folder_name, datetime.now()
    
    def get_result_folders_by_experiment(self) -> Dict[str, List[Tuple[str, datetime]]]:
        """
        Group result folders by experiment name
        
        Returns:
            Dictionary mapping experiment names to list of (folder_path, timestamp) tuples
        """
        if not os.path.exists(self.result_base_folder):
            return {}
        
        experiments = defaultdict(list)
        
        for folder_name in os.listdir(self.result_base_folder):
            folder_path = os.path.join(self.result_base_folder, folder_name)
            if os.path.isdir(folder_path):
                experiment_name, timestamp = self._parse_result_folder(folder_name)
                experiments[experiment_name].append((folder_path, timestamp))
        
        # Sort each experiment's folders by timestamp (newest first)
        for exp_name in experiments:
            experiments[exp_name].sort(key=lambda x: x[1], reverse=True)
        
        return experiments
    
    def cleanup_old_results(self, dry_run: bool = False, keep_count: int = 1) -> Dict[str, int]:
        """
        Clean up old result folders, keeping only the most recent ones for each experiment
        
        Args:
            dry_run: If True, only show what would be deleted without actually deleting
            keep_count: Number of most recent results to keep per experiment
        
        Returns:
            Dictionary with cleanup statistics
        """
        experiments = self.get_result_folders_by_experiment()
        stats = {
            'experiments_found': len(experiments),
            'folders_deleted': 0,
            'folders_kept': 0,
            'total_size_freed': 0,
            'errors': 0
        }
        
        if not experiments:
            print("No result folders found.")
            return stats
        
        print(f"\nFound {len(experiments)} experiment(s) with results:")
        
        for exp_name, folders in experiments.items():
            print(f"\n  {exp_name}: {len(folders)} result folder(s)")
            
            if len(folders) <= keep_count:
                print(f"    → Keeping all {len(folders)} folder(s) (at or below keep limit)")
                stats['folders_kept'] += len(folders)
                continue
            
            # Keep the most recent ones
            folders_to_keep = folders[:keep_count]
            folders_to_delete = folders[keep_count:]
            
            stats['folders_kept'] += len(folders_to_keep)
            stats['folders_deleted'] += len(folders_to_delete)
            
            if self.verbose:
                print(f"    Keeping {keep_count} most recent:")
                for folder_path, timestamp in folders_to_keep:
                    print(f"      ✓ {os.path.basename(folder_path)} ({timestamp.strftime('%Y-%m-%d %H:%M:%S')})")
            else:
                print(f"    → Keeping {keep_count} most recent folder(s)")
            
            print(f"    Removing {len(folders_to_delete)} older folder(s):")
            for folder_path, timestamp in folders_to_delete:
                folder_size = self._get_folder_size(folder_path)
                stats['total_size_freed'] += folder_size
                size_mb = folder_size / (1024 * 1024)
                
                if dry_run:
                    print(f"      [DRY-RUN] Would delete: {os.path.basename(folder_path)} ({timestamp.strftime('%Y-%m-%d %H:%M:%S')}, {size_mb:.2f} MB)")
                else:
                    try:
                        print(f"      ✗ Deleting: {os.path.basename(folder_path)} ({timestamp.strftime('%Y-%m-%d %H:%M:%S')}, {size_mb:.2f} MB)")
                        shutil.rmtree(folder_path)
                    except Exception as e:
                        print(f"      ⚠ Error deleting {os.path.basename(folder_path)}: {e}")
                        stats['errors'] += 1
                        stats['folders_deleted'] -= 1
                        stats['total_size_freed'] -= folder_size
        
        return stats
    
    def cleanup_all_results(self, dry_run: bool = False) -> Dict[str, int]:
        """
        Remove all result folders
        
        Args:
            dry_run: If True, only show what would be deleted without actually deleting
        
        Returns:
            Dictionary with cleanup statistics
        """
        stats = {
            'folders_deleted': 0,
            'total_size_freed': 0,
            'errors': 0
        }
        
        if not os.path.exists(self.result_base_folder):
            print("No result folders found.")
            return stats
        
        folders = [
            os.path.join(self.result_base_folder, f)
            for f in os.listdir(self.result_base_folder)
            if os.path.isdir(os.path.join(self.result_base_folder, f))
        ]
        
        if not folders:
            print("No result folders found.")
            return stats
        
        print(f"\nFound {len(folders)} result folder(s) to remove:")
        
        for folder_path in folders:
            folder_size = self._get_folder_size(folder_path)
            stats['total_size_freed'] += folder_size
            stats['folders_deleted'] += 1
            size_mb = folder_size / (1024 * 1024)
            
            if dry_run:
                print(f"  [DRY-RUN] Would delete: {os.path.basename(folder_path)} ({size_mb:.2f} MB)")
            else:
                try:
                    print(f"  ✗ Deleting: {os.path.basename(folder_path)} ({size_mb:.2f} MB)")
                    shutil.rmtree(folder_path)
                except Exception as e:
                    print(f"  ⚠ Error deleting {os.path.basename(folder_path)}: {e}")
                    stats['errors'] += 1
                    stats['folders_deleted'] -= 1
                    stats['total_size_freed'] -= folder_size
        
        return stats
    
    def cleanup_experiment_data(self, dry_run: bool = False) -> Dict[str, int]:
        """
        Remove experiment data folders
        
        Args:
            dry_run: If True, only show what would be deleted without actually deleting
        
        Returns:
            Dictionary with cleanup statistics
        """
        stats = {
            'folders_deleted': 0,
            'total_size_freed': 0,
            'errors': 0
        }
        
        if not os.path.exists(self.experiment_folder):
            print("No experiment data folders found.")
            return stats
        
        folders = [
            os.path.join(self.experiment_folder, f)
            for f in os.listdir(self.experiment_folder)
            if os.path.isdir(os.path.join(self.experiment_folder, f))
        ]
        
        if not folders:
            print("No experiment data folders found.")
            return stats
        
        print(f"\nFound {len(folders)} experiment data folder(s) to remove:")
        
        for folder_path in folders:
            folder_size = self._get_folder_size(folder_path)
            stats['total_size_freed'] += folder_size
            stats['folders_deleted'] += 1
            size_mb = folder_size / (1024 * 1024)
            
            if dry_run:
                print(f"  [DRY-RUN] Would delete: {os.path.basename(folder_path)} ({size_mb:.2f} MB)")
            else:
                try:
                    print(f"  ✗ Deleting: {os.path.basename(folder_path)} ({size_mb:.2f} MB)")
                    shutil.rmtree(folder_path)
                except Exception as e:
                    print(f"  ⚠ Error deleting {os.path.basename(folder_path)}: {e}")
                    stats['errors'] += 1
                    stats['folders_deleted'] -= 1
                    stats['total_size_freed'] -= folder_size
        
        return stats
    
    def _get_folder_size(self, folder_path: str) -> int:
        """
        Calculate total size of a folder in bytes
        
        Args:
            folder_path: Path to folder
        
        Returns:
            Total size in bytes
        """
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(folder_path):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
        except Exception:
            pass
        return total_size
    
    def print_summary(self, stats: Dict[str, int], operation: str):
        """
        Print a summary of cleanup operations
        
        Args:
            stats: Statistics dictionary from cleanup operation
            operation: Description of the operation performed
        """
        print(f"\n{'='*60}")
        print(f"Cleanup Summary - {operation}")
        print(f"{'='*60}")
        
        for key, value in stats.items():
            if key == 'total_size_freed':
                size_mb = value / (1024 * 1024)
                size_gb = value / (1024 * 1024 * 1024)
                if size_gb >= 1:
                    print(f"  {key.replace('_', ' ').title()}: {size_gb:.2f} GB")
                else:
                    print(f"  {key.replace('_', ' ').title()}: {size_mb:.2f} MB")
            else:
                print(f"  {key.replace('_', ' ').title()}: {value}")
        
        if stats.get('errors', 0) > 0:
            print(f"\n  ⚠ Warning: {stats['errors']} folder(s) could not be deleted")
        
        print(f"{'='*60}\n")
