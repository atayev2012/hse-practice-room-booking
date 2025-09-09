from gspread import Spreadsheet
from datetime import date, timedelta
from config import config

data_dict = {}

# result structure
# data_dict = {
#       building : {
#           room_number: {
#               date: {
#                   time_slot: available or not
#                       }
#                   }
#               }
#           }

# TODO: Generate list of dates for specific module (starting from today or module start date)
# TODO: Generate dates based on cell content

async def load_and_parse(spreadsheet: Spreadsheet):
    global data_dict

    worksheets = spreadsheet.worksheets()
    for worksheet in worksheets:
        if data_dict.get(worksheet.title):
            continue
        else:
            # create key => building address Ex: 'Родионова', 'Б.Печерская', 'Костина', 'Львовская', 'Сормово'
            data_dict[worksheet.title] = {}

            worksheet_data = worksheet.get_all_values()
            for i, room in enumerate(worksheet_data[1][2:]):
                if worksheet_data[2][i + 2] != "" or worksheet_data[3][i + 2] != "":
                    if room.lower() == "коворкинг" or (room == "" and worksheet_data[1][i + 1].lower() == "коворкинг"):
                        room = worksheet_data[2][i + 2]
                    # print(f"{worksheet.title}: {room}")
                    data_dict[worksheet.title][room.lower()] = {}
                    data_dict[worksheet.title][room.lower()]["equipment"] = [k.strip().lower() for k in worksheet_data[2][i + 2].split("\n") if k.strip() != ""]
                    data_dict[worksheet.title][room.lower()]["capacity"] = worksheet_data[3][i + 2].lower()
        # print(f"{worksheet.title} => {worksheet_data}")
        # print(worksheet.title)
        # print(worksheet.get_all_values())


# Verify if week is upper (else it is lower)
async def is_upper_week(
        target_date: date,
        education_start_date: date = config.MODULE_I_START,
        education_end_date: date = config.MODULE_IV_END
) -> bool | None:
    """
    :param target_date: The date to be checked if it is in an upper week
    :param education_start_date: The date indicating start of education
    :param education_end_date: The date indicating end of education

    :return: 'True' if it is upper week, 'False' otherwise (None in case of date validation error)
    """

    if not isinstance(target_date, date) or target_date < education_start_date or target_date > education_end_date:
        return None

    education_start_weekday = education_start_date.weekday()

    # If first week starts with any day above 5 (Saturday) then move higher week to next week
    # else make higher week with current week by moving date to Monday of the same week
    if education_start_weekday > 5:
        first_week_start_date = education_start_date + timedelta(days=7 - education_start_weekday)
    else:
        first_week_start_date = education_start_date - timedelta(days=education_start_weekday)

    # calculate date difference between two dates + calculate weeks + identify if even or odd
    time_diff = target_date - first_week_start_date
    return (time_diff.days // 7) % 2 == 0


if __name__ == '__main__':
    pass