from gspread import Spreadsheet

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


if __name__ == '__main__':
    pass