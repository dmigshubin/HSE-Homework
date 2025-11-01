greet() {
	echo "Hello, $1"
}

sum() {
	echo $(( $1 + $2 ))
}

greet "Dmitrii"

result=$(sum "$1" "$2")
echo "Сумма: $result"
