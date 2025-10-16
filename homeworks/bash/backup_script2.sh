read -p "Введите название файла:" file_name
if find . -type f -name "$file_name" | grep -q .; then
	echo "Файл '$file_name' найден"
else
	echo "Файл '$file_name' не найден"
fi 
