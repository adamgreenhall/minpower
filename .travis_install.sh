sudo apt-get install glpk
conda install --yes python=$TRAVIS_PYTHON_VERSION --file requirements.conda.txt
pip install .

if [ x"$FULL_DEPS" == x"true" ]; then
    echo "Installing FULL_DEPS"
    conda install --yes python=$TRAVIS_PYTHON_VERSION --file requirements.conda.full_deps.txt
fi
