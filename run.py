import argparse
from app import create_app

def main():
    parser = argparse.ArgumentParser(description='Docker/Podman Container Test Manager')
    parser.add_argument('--backend', choices=['docker', 'podman'], default='docker',
                      help='Container backend to use (default: docker)')
    args = parser.parse_args()
    
    app = create_app(backend_type=args.backend)
    app.run(debug=True)

if __name__ == '__main__':
    main() 