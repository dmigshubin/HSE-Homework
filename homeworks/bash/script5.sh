read -p "Введите путь к директории: " dir_path

if [ -d "$dir_path" ]; then
        cd "$dir_path"
        for file in *; do
                if [ -f "$file" ]; then
                        cp "$file" "backup_$file"

                elif [ -d "$file" ]; then
                        cp -r "$file" "backup_$file"
                fi
        done
else
    echo "Директория не найдена!"
fi
