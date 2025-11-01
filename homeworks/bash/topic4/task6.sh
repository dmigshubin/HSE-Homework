echo "Содержимое input.txt"
cat input.txt

wc -l < input.txt > output.txt

ls nonexistent_file 2> error.log
