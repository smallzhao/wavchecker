for file in newsample/OK/*; do echo -n $file && ./lossenergy $file; done
for file in newsample/OKTOO/*; do echo -n $file && ./lossenergy $file; done
for file in newsample/LOSS/*; do echo -n $file && ./lossenergy $file; done
