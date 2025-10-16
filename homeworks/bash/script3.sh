read -p "Введите путь к директории для архивации: " dir

if [ ! -d "$dir" ]; then
	echo "Дирректория '$dir' не найдена!"
	exit 1
fi

dirname=$(basename "$dir")

today=$(date +%F)

archive_name="${dirname}_${today}.tar.gz"

tar -czf "$archive_name" -C "$(dirname) "$dir")" "$dirname"

echo "Архив создан: $archive_name"
