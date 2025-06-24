import sys
import subprocess

def main():
    result = subprocess.run([sys.executable, '-m', 'pytest', 'claude/tests'], capture_output=False)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
