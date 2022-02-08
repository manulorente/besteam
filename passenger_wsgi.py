import sys, os
INTERP = os.path.join(os.environ['HOME'], 'besteam.dreamhosters.com', 'venv', 'bin', 'python3')
if sys.executable != INTERP:
        os.execl(INTERP, INTERP, *sys.argv)
sys.path.append(os.getcwd())
sys.path.append('~/besteam.dreamhosters.com/app')
from app.routes import app as application

if __name__ == '__main__':
    application.run(debug=False)
