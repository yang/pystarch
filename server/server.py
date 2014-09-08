from flask import Flask, request, render_template
from subprocess import Popen, PIPE

app = Flask(__name__)


def analyze(source):
    process = Popen(['python2', '../main.py'],
                    stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate(source)
    return (stdout, True) if process.returncode == 0 else (stderr, False)


@app.route('/html', methods=['POST'])
def html():
    source = request.form.get('source')
    output, success = analyze(source)
    result = output.replace('\n', '\n<br/>\n')
    return result if success else (result, 400)


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0')
