sudo apt-get install python-numpy glpk
pip install --use-mirrors .

if [ x"$FULL_DEPS" == x"true" ]; then
    echo "Installing FULL_DEPS"
    sudo apt-get install libhdf5-serial-dev
    pip install numexpr cython
    pip install tables matplotlib
fi
