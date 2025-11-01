# 1 Список файлов и их тип
echo "Список файлов:"
for i in *; do
	file "$i"
done

# 2 Проверка наличия файла
if [ -z "$1" ]; then
	echo "Укажите имя файла "
else
	if [ -e "$1" ]; then
		echo "Файл '$1' существует."
	else
		echo "Файл '$1' не найден."
	fi
fi

#3 Имя и права доступа
echo -e "\nИнформация о файлах:"
for i in *; do
	perms=$(ls -ld "$i" | awk '{print $1}')
	echo "$i - $perms"
done
