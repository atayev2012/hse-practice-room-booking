from config import config
from openpyxl import Workbook
from openpyxl.styles import Alignment
from openpyxl.worksheet.table import Table, TableStyleInfo
from uuid import uuid4
import os
from database.utils import get_all_records_n_days


# Export records for specified days to .xlsx file
async def export_database() -> str | None:
    """
    Creates temporary .xlsx file with last one-week data from records table

    Returns:
        (str | None): File name or "None" if failed to create file
    """
    try:
        # Create temp folder if it does not exist
        current_directory = os.getcwd()
        temp_path = os.path.join(current_directory, "bot", "admin", "temp")
        os.makedirs(temp_path, exist_ok=True)

        # Load records from database
        loaded_data = await get_all_records_n_days()

        # Convert data to list with items
        converted_data = [
            ["№ записи", "ФИО", "Тип пользователя", "Telegram", "Телефон", "Email", "Здание", "Аудитория", "Дата", "Временной слот"]
        ]
        for item in loaded_data:
            converted_data.append(
                [
                    item.id,
                    item.user.full_name,
                    item.user.user_type,
                    f"https://t.me/{item.user.username}" if item.user.username else f"tg://user?id={item.user.telegram_id}",
                    item.user.phone,
                    item.user.email,
                    item.building,
                    item.room,
                    item.date,
                    f"{item.time_slot_start.strftime("%H:%M")}-{item.time_slot_end.strftime("%H:%M")}"
                ]
            )

        # Create workbook
        wb = Workbook()
        sheet = wb.active

        # Generate worksheet title based on config.DAYS_TO_LOAD_FROM_DB
        sheet.title = await generate_worksheet_title(config.DAYS_TO_LOAD_FROM_DB)

        # Add converted data to workbook
        for row in converted_data:
            sheet.append(row)

        # Creating style for new table
        style = TableStyleInfo(
            name="TableStyleMedium9", showFirstColumn=False,
            showLastColumn=False, showRowStripes=True, showColumnStripes=False
        )

        # Creating new table for data
        table = Table(displayName="Записи", ref=f"A1:J{len(converted_data)}", tableStyleInfo=style)

        # Adding table to the sheet
        sheet.add_table(table)

        # Adjust width of columns
        for column in sheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for i, cell in enumerate(column):
                if i != 0:
                    # Formatting dates
                    if column_letter == "I":
                        cell.number_format = "DD.MM.YYYY"

                    if column_letter == "D":
                        cell.hyperlink = cell.value

                    if column_letter == "F":
                        cell.hyperlink = f"mailto:{cell.value}"

                    if column_letter in ["H", "I", "J", "A"]:
                        cell.alignment = Alignment(horizontal="center")

                # Updating max_length
                if cell.value:
                    cell_length = len(str(cell.value))
                    if cell_length > max_length:
                        max_length = cell_length

            # Adjust column width based on the longest cell content
            sheet.column_dimensions[column_letter].width = max_length + 2

        # Create temporary .xlsx file by saving file
        temp_file_name = f"{str(uuid4())}.xlsx"
        temp_file_path = os.path.join(temp_path, temp_file_name)
        wb.save(temp_file_path)

        return temp_file_name
    except Exception as e:
        print(e)


# Generate worksheet title based on config.DAYS_TO_LOAD_FROM_DB
async def generate_worksheet_title(n: int) -> str:
    days = ["день", "дня", "дней"]
    last = ["последний", "последние"]

    result_str = "Записи за "
    tenth_remainder = n % 10
    hundreds_remainder = n % 100

    if tenth_remainder == 1 and (hundreds_remainder > 11 or hundreds_remainder == 1):
        result_str += f"{last[0]} {n} {days[0]}"
    elif 2 <= tenth_remainder <= 4 and (hundreds_remainder > 21 or hundreds_remainder < 5):
        result_str += f"{last[1]} {n} {days[1]}"
    else:
        result_str += f"{last[1]} {n} {days[2]}"

    return result_str
