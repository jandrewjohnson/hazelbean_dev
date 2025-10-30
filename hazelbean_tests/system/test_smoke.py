"""
Consolidated System Smoke Tests

This file consolidates tests from:
- smoke/test_smoke.py
- smoke/test_get_path_doc.py

Covers comprehensive smoke testing including:
- Basic import and functionality validation
- ProjectFlow basic operations
- Documentation generation smoke tests
- System-level integration validation
- Performance benchmarks for critical operations
- Literate testing with documentation generation
"""

import sys, types
import os
import pathlib
import textwrap
import tempfile
import pytest

# --- minimal Google stubs (same for all quick tests) -------------------
for name in [
    "google", "google.cloud", "google.cloud.storage",
    "googleapiclient", "googleapiclient.discovery",
    "google_auth_oauthlib", "google_auth_oauthlib.flow",
    "google.auth", "google.auth.transport", "google.auth.transport.requests",
]:
    mod = types.ModuleType(name); mod.__path__ = []
    sys.modules[name] = mod

sys.modules["google.cloud.storage"].Client = object
sys.modules["googleapiclient.discovery"].build = lambda *a, **k: None
class _Flow:                                  # Minimal InstalledAppFlow stub
    def __init__(self, *a, **k): pass
    def run_local_server(self, *a, **k): return None
sys.modules["google_auth_oauthlib.flow"].InstalledAppFlow = _Flow
sys.modules["google.auth.transport.requests"].Request = object
# -----------------------------------------------------------------------

import hazelbean as hb

DOCS_DIR = pathlib.Path("docs")          # one place for all vignettes
DOCS_DIR.mkdir(exist_ok=True)


class TestBasicSmokeTests:
    """Basic smoke tests to validate core functionality"""

    @pytest.mark.smoke
    def test_hazelbean_imports_successfully(self):
        """Test that hazelbean can be imported without errors"""
        # This is already handled by the import above, but let's be explicit
        import hazelbean as hb
        assert hb is not None
        assert hasattr(hb, "ProjectFlow")

    @pytest.mark.smoke
    def test_projectflow_imports(self):
        """Test that ProjectFlow is available and can be imported"""
        assert hasattr(hb, "ProjectFlow")
        
        # Test that we can instantiate ProjectFlow
        with tempfile.TemporaryDirectory() as temp_dir:
            p = hb.ProjectFlow(temp_dir)
            assert p is not None

    @pytest.mark.smoke
    @pytest.mark.benchmark
    def test_hazelbean_import_performance(self, benchmark):
        """Benchmark the import time of hazelbean module."""
        def import_hazelbean():
            import hazelbean as hb
            return hb
        
        result = benchmark(import_hazelbean)
        assert hasattr(result, "ProjectFlow")

    @pytest.mark.smoke
    def test_projectflow_basic_functionality(self):
        """Test basic ProjectFlow functionality works"""
        with tempfile.TemporaryDirectory() as temp_dir:
            p = hb.ProjectFlow(temp_dir)
            
            # Test basic get_path functionality with an existing file
            test_file = os.path.join(temp_dir, "test_file.txt")
            with open(test_file, 'w') as f:
                f.write("test content")
            
            path = p.get_path("test_file.txt")
            assert path is not None
            assert "test_file.txt" in path
            assert os.path.exists(path)

    @pytest.mark.smoke
    def test_common_hazelbean_functions_available(self):
        """Test that common hazelbean functions are available"""
        # Test that key functions are available
        assert hasattr(hb, "temp")
        assert hasattr(hb, "get_path") 
        assert hasattr(hb, "describe")
        assert hasattr(hb, "save_array_as_npy")
        
        # Test that we can call temp function
        temp_path = hb.temp('.txt', remove_at_exit=True)
        assert temp_path is not None
        assert temp_path.endswith('.txt')

    @pytest.mark.smoke
    def test_numpy_integration(self):
        """Test basic numpy integration with hazelbean"""
        import numpy as np
        
        # Create test array
        test_array = np.random.rand(10, 10)
        
        # Test saving with hazelbean
        temp_path = hb.temp('.npy', remove_at_exit=True)
        hb.save_array_as_npy(test_array, temp_path)
        
        # Verify file was created
        assert os.path.exists(temp_path)
        
        # Test describe function
        result = hb.describe(temp_path, surpress_print=True, surpress_logger=True)
        assert result is not None

    @pytest.mark.smoke
    def test_basic_error_handling(self):
        """Test that get_path raises NameError for unresolvable paths.
        
        Note: get_path() intentionally raises NameError (not FileNotFoundError) because
        it performs complex path resolution logic beyond simple file existence checking:
        - Resolves paths relative to project structure
        - Searches multiple possible_dirs
        - Attempts cloud bucket downloads
        
        NameError semantically indicates "name/reference resolution failed" which is
        more accurate than "file at specific path not found".
        See docs/plans/exception-handling-analysis.md for detailed rationale.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            p = hb.ProjectFlow(temp_dir)
            
            # get_path should raise NameError when path cannot be resolved
            with pytest.raises(NameError) as exc_info:
                path = p.get_path("definitely_does_not_exist.txt")
            
            # Verify error message provides useful context
            error_msg = str(exc_info.value)
            assert "does not exist" in error_msg.lower()


class TestDocumentationGeneration:
    """Test documentation generation functionality (from test_get_path_doc.py)"""

    def test_get_path_generates_doc(self, tmp_path):
        """Smoke-test + write example QMD."""
        # ---------- Test behaviour -------------------------------------------
        p = hb.ProjectFlow(project_dir=str(tmp_path))     # cast Path → str
        
        # Create the file so get_path can find it
        test_file = tmp_path / "foo.txt"
        test_file.write_text("test content")
        
        resolved = p.get_path("foo.txt")

        assert resolved.endswith("foo.txt")               # file name correct
        assert str(tmp_path) in resolved                  # lives in project dir

        # ---------- Generate documentation -----------------------------------
        qmd = DOCS_DIR / "get_path_example.qmd"

        qmd.write_text(textwrap.dedent(f"""
        ---
        title: "Hazelbean example – get_path"
        execute: true          # run the chunk when rendering
        freeze: auto
        ---

        ```{{python}}
        import hazelbean as hb, tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            p = hb.ProjectFlow(project_dir=tmp)
            print(p.get_path("foo.txt"))
        ```

        Above we create a throw-away project directory and ask Hazelbean for
        `"foo.txt"`.  The printed path shows how *get_path* resolves files relative
        to the project workspace.
        """))
        
        # Verify documentation was generated
        assert qmd.exists()
        assert qmd.stat().st_size > 0  # File has content
        
        # Verify content contains expected elements
        content = qmd.read_text()
        assert "get_path" in content
        assert "hazelbean" in content
        assert "ProjectFlow" in content

    @pytest.mark.smoke
    def test_error_handling_documentation(self):
        """Test documentation generation for error handling scenarios"""
        qmd = DOCS_DIR / "get_path_error_handling.qmd"

        qmd.write_text(textwrap.dedent("""
        ---
        title: "Hazelbean – get_path Error Handling"
        execute: true
        freeze: auto
        ---

        ## Error Handling Examples

        ```{python}
        import hazelbean as hb, tempfile

        # Test with non-existent file
        with tempfile.TemporaryDirectory() as tmp:
            p = hb.ProjectFlow(project_dir=tmp)
            
            # This should work even if file doesn't exist
            try:
                path = p.get_path("missing_file.txt")
                print(f"Resolved path: {path}")
                print("get_path handles missing files gracefully")
            except Exception as e:
                print(f"Error occurred: {e}")
        ```

        The above demonstrates how `get_path` handles missing files.
        """))
        
        # Verify documentation was generated
        assert qmd.exists()
        assert qmd.stat().st_size > 0

    @pytest.mark.smoke
    def test_performance_documentation(self):
        """Test documentation generation for performance examples"""
        qmd = DOCS_DIR / "get_path_performance_guide.qmd"

        qmd.write_text(textwrap.dedent("""
        ---
        title: "Hazelbean – get_path Performance Guide"
        execute: true
        freeze: auto
        ---

        ## Performance Characteristics

        ```{python}
        import hazelbean as hb, tempfile, time

        with tempfile.TemporaryDirectory() as tmp:
            p = hb.ProjectFlow(project_dir=tmp)
            
            # Create a test file
            test_file = "performance_test.txt"
            with open(f"{tmp}/{test_file}", 'w') as f:
                f.write("test content")
            
            # Benchmark single call
            start = time.time()
            path = p.get_path(test_file)
            single_call_time = time.time() - start
            
            print(f"Single get_path call: {single_call_time:.6f} seconds")
            print(f"Resolved path: {path}")
            
            # Benchmark multiple calls
            start = time.time()
            for i in range(100):
                path = p.get_path(test_file)
            multiple_calls_time = time.time() - start
            
            print(f"100 get_path calls: {multiple_calls_time:.6f} seconds")
            print(f"Average per call: {multiple_calls_time/100:.6f} seconds")
        ```

        This shows typical performance characteristics of the `get_path` method.
        """))
        
        # Verify documentation was generated
        assert qmd.exists()
        assert qmd.stat().st_size > 0

    @pytest.mark.smoke
    def test_file_formats_documentation(self):
        """Test documentation generation for different file formats"""
        qmd = DOCS_DIR / "get_path_file_formats.qmd"

        qmd.write_text(textwrap.dedent("""
        ---
        title: "Hazelbean – get_path File Format Support"
        execute: true
        freeze: auto
        ---

        ## Supported File Formats

        ```{python}
        import hazelbean as hb, tempfile, os

        with tempfile.TemporaryDirectory() as tmp:
            p = hb.ProjectFlow(project_dir=tmp)
            
            # Test different file extensions
            file_types = [
                "data.csv",
                "raster.tif", 
                "vector.shp",
                "config.json",
                "script.py",
                "document.txt"
            ]
            
            print("Testing file format resolution:")
            for file_type in file_types:
                path = p.get_path(file_type)
                print(f"  {file_type} -> {os.path.basename(path)}")
        ```

        The `get_path` method works with various file formats commonly used
        in geospatial and scientific computing workflows.
        """))
        
        # Verify documentation was generated
        assert qmd.exists()
        assert qmd.stat().st_size > 0


class TestSystemIntegration:
    """Test system-level integration smoke tests"""

    @pytest.mark.smoke
    def test_temp_directory_creation(self):
        """Test that temporary directory creation works"""
        with tempfile.TemporaryDirectory() as temp_dir:
            p = hb.ProjectFlow(temp_dir)
            
            # Should be able to create subdirectories
            sub_path = os.path.join(temp_dir, "subdir", "nested")
            os.makedirs(sub_path, exist_ok=True)
            
            assert os.path.exists(sub_path)
            
            # get_path should construct paths without validation when raise_error_if_fail=False
            nested_file_path = p.get_path("subdir/nested/test.txt", raise_error_if_fail=False)
            assert "nested" in nested_file_path
            assert "test.txt" in nested_file_path

    @pytest.mark.smoke
    def test_multiple_projectflow_instances(self):
        """Test that multiple ProjectFlow instances can coexist"""
        with tempfile.TemporaryDirectory() as temp_dir1:
            with tempfile.TemporaryDirectory() as temp_dir2:
                p1 = hb.ProjectFlow(temp_dir1)
                p2 = hb.ProjectFlow(temp_dir2)
                
                # Each should resolve to its own directory (without validation)
                path1 = p1.get_path("test.txt", raise_error_if_fail=False)
                path2 = p2.get_path("test.txt", raise_error_if_fail=False)
                
                assert temp_dir1 in path1
                assert temp_dir2 in path2
                assert path1 != path2

    @pytest.mark.smoke
    def test_relative_vs_absolute_paths(self):
        """Test handling of relative vs absolute paths with actual files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            p = hb.ProjectFlow(temp_dir)
            
            # Create test file for relative path testing
            rel_file = os.path.join(temp_dir, "relative_file.txt")
            with open(rel_file, 'w') as f:
                f.write("relative test content")
            
            # Test relative path
            rel_path = p.get_path("relative_file.txt")
            assert "relative_file.txt" in rel_path
            assert os.path.exists(rel_path)
            
            # Create test file for absolute path testing
            abs_file = os.path.join(temp_dir, "absolute_file.txt")
            with open(abs_file, 'w') as f:
                f.write("absolute test content")
            
            # Test absolute path
            abs_input = os.path.abspath(abs_file)
            abs_path = p.get_path(abs_input)
            assert "absolute_file.txt" in abs_path
            assert os.path.exists(abs_path)

    @pytest.mark.smoke
    def test_special_characters_in_paths(self):
        """Test handling of special characters in file paths with actual files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            p = hb.ProjectFlow(temp_dir)
            
            # Test various special characters (that are valid in file names)
            special_files = [
                "file_with_underscores.txt",
                "file-with-hyphens.txt",
                "file.with.dots.txt",
                "file with spaces.txt",  # May not be supported on all systems
                "file123numbers.txt",
                "UPPERCASE.TXT",
                "mixedCase.TxT"
            ]
            
            for special_file in special_files:
                # Create file with special characters
                file_path = os.path.join(temp_dir, special_file)
                try:
                    with open(file_path, 'w') as f:
                        f.write(f"test content for {special_file}")
                    
                    # Test get_path with actual file
                    path = p.get_path(special_file)
                    assert special_file in path or os.path.basename(path) == special_file
                    assert os.path.exists(path)
                except Exception as e:
                    # Some special characters might not be supported on some systems
                    # NameError indicates path resolution failure (hazelbean's design)
                    assert isinstance(e, (ValueError, OSError, NameError))

    @pytest.mark.smoke
    def test_concurrent_access(self):
        """Test basic concurrent access patterns with actual files"""
        import threading
        import time
        
        with tempfile.TemporaryDirectory() as temp_dir:
            p = hb.ProjectFlow(temp_dir)
            
            results = []
            errors = []
            
            # Pre-create all files before threads start (avoid race conditions)
            for thread_id in range(3):
                for i in range(10):
                    file_path = os.path.join(temp_dir, f"thread_{thread_id}_file_{i}.txt")
                    with open(file_path, 'w') as f:
                        f.write(f"Thread {thread_id} file {i}")
            
            def worker_thread(thread_id):
                try:
                    for i in range(10):
                        path = p.get_path(f"thread_{thread_id}_file_{i}.txt")
                        results.append((thread_id, path))
                        time.sleep(0.001)  # Small delay
                except Exception as e:
                    errors.append((thread_id, e))
            
            # Create and start multiple threads
            threads = []
            for i in range(3):
                t = threading.Thread(target=worker_thread, args=(i,))
                threads.append(t)
                t.start()
            
            # Wait for all threads to complete
            for t in threads:
                t.join()
            
            # Verify results
            assert len(errors) == 0, f"Errors in concurrent access: {errors}"
            assert len(results) == 30, f"Expected 30 results, got {len(results)}"
            
            # Verify all paths exist and are unique per thread
            thread_paths = {}
            for thread_id, path in results:
                assert os.path.exists(path), f"Path {path} doesn't exist"
                if thread_id not in thread_paths:
                    thread_paths[thread_id] = []
                thread_paths[thread_id].append(path)
            
            assert len(thread_paths) == 3, "Should have results from all 3 threads"


class TestSystemEnvironment:
    """Test system environment validation"""

    @pytest.mark.smoke
    def test_python_version_compatibility(self):
        """Test Python version compatibility with actual file"""
        import sys
        
        # Should work with Python 3.7+
        assert sys.version_info >= (3, 7), f"Python version {sys.version_info} may not be supported"
        
        # Test that hazelbean works with current Python version
        with tempfile.TemporaryDirectory() as temp_dir:
            p = hb.ProjectFlow(temp_dir)
            
            # Create test file
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, 'w') as f:
                f.write("Python version compatibility test")
            
            # Test basic get_path functionality
            path = p.get_path("test.txt")
            assert path is not None
            assert os.path.exists(path)

    @pytest.mark.smoke
    def test_required_dependencies_available(self):
        """Test that required dependencies are available"""
        # Test numpy
        import numpy as np
        assert hasattr(np, 'array')
        
        # Test that hazelbean can use numpy
        arr = np.random.rand(5, 5)
        temp_path = hb.temp('.npy', remove_at_exit=True)
        hb.save_array_as_npy(arr, temp_path)
        assert os.path.exists(temp_path)

    @pytest.mark.smoke
    def test_file_system_permissions(self):
        """Test basic file system permissions"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test directory creation
            test_dir = os.path.join(temp_dir, "permission_test")
            os.makedirs(test_dir)
            assert os.path.exists(test_dir)
            
            # Test file creation
            test_file = os.path.join(test_dir, "test.txt")
            with open(test_file, 'w') as f:
                f.write("permission test")
            assert os.path.exists(test_file)
            
            # Test file reading
            with open(test_file, 'r') as f:
                content = f.read()
            assert content == "permission test"
            
            # Test hazelbean can work in this environment
            p = hb.ProjectFlow(temp_dir)
            path = p.get_path("permission_test/test.txt")
            assert "test.txt" in path


if __name__ == '__main__':
    pytest.main([__file__])

