import asyncio
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.chat_member_updated import \
    ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.types import ChatMemberUpdated
import requests
import os
from dotenv import load_dotenv
import json

load_dotenv()
API_TOKEN = os.getenv('API_TOKEN')
file_path = 'data.json'

messages = {}
sums = {}
last_sum = {}


bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()
router.my_chat_member.filter(F.chat)

def save_data():
    data = {'messages': messages, 'sums':sums}
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

def concat_messages(id):
    d = messages[id]
    return '\n'.join([v for k,v in sorted(d.items(), key=lambda x:x[0])])

@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def bot_added(event: ChatMemberUpdated):
    t = event.chat.id
    messages[t] = {}
    sums[t] = []
    await event.answer("Спасибо за добавление в чат! Теперь я могу суммировать диалоги и генерировать отчеты.")


@dp.message(Command('start'))
async def send_welcome(message: types.Message):
    await message.reply("Привет!")

@dp.message(Command('summarize'))
async def summarize_dialog(message: types.Message):
    global last_sum
    dialog = concat_messages(message.chat.id)
    try:
        response = requests.post('http://127.0.0.1:8000/summarize', json={"dialog": dialog})
        summary = response.json().get('summary', 'Ошибка суммаризации')
        last_sum[message.chat.id] = summary
    except:
        summary = "Что-то пошло не так"
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="Сохранить", callback_data="sum_save"))
    builder.add(types.InlineKeyboardButton(
        text="Отмена", callback_data="sum_del"))
    await message.reply(summary, reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("sum_"))
async def save_sum(callback: types.CallbackQuery):
    flag = callback.data.split("_")[1]=='save'
    chat_id = callback.message.chat.id
    await bot.delete_message(chat_id, callback.message.message_id)
    if flag:
        sums[chat_id].append(last_sum[chat_id])
        messages[chat_id] = {}
        save_data()
    last_sum[chat_id] = ""

@dp.message(Command('mes'))
async def mes(message: types.Message):
    dialog = "Сохраненные сообщения:\n" + concat_messages(message.chat.id)
    await message.reply(dialog)

@dp.message(Command('sums'))
async def get_sums(message: types.Message):
    dialog = "Сохраненные суммаризации:\n" + '\n'.join(sums[message.chat.id])
    await message.reply(dialog)

@dp.message(Command('save'))
async def save(message: types.Message):
    save_data()

@dp.message(Command('report'))
async def generate_report(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="Да", callback_data="ans_yes"))
    builder.add(types.InlineKeyboardButton(
        text="Нет", callback_data="ans_no"))

    await message.reply("Учитывать последние сообщения?", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("ans_"))
async def gen_rep(callback: types.CallbackQuery):
    flag = callback.data.split("_")[1]=='yes'
    m = callback.message
    await bot.delete_message(m.chat.id, m.message_id)
    summaries = '\n'.join(sums[m.chat.id])
    if flag:
        summaries = summaries + '\n' + '\n'.join(messages[m.chat.id].values())
    try:
        response = requests.post('http://127.0.0.1:8000/report', json={"summaries": summaries})
        report = response.json().get('report', 'Ошибка генерации отчета')
    except:
        report = "Что-то пошло не так"
    await callback.message.answer(report)


@dp.edited_message()
async def edited_message(message: types.Message):
    global messages
    user = message.from_user
    m = f'{user.full_name}: {message.text}'
    print(m)
    t = message.chat.id
    messages[t][message.message_id] = m


@dp.message()
async def save_message(message: types.Message):
    global messages
    if message.text == None:
        return 
    user = message.from_user
    m = f'{user.full_name}: {message.text}'
    print(m)
    t = message.chat.id
    if t not in messages:
        messages[t] = {}
    messages[t][message.message_id] = m

async def init_vars():
    global messages, sums
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as openfile:
            data = json.load(openfile, object_hook=lambda d: {int(k) if k.lstrip('-').isdigit() else k: v for k, v in d.items()})
            print(data)
            messages = data['messages']
            sums = data['sums']
    else:
        messages = {}
        sums = {}

async def main():
    await init_vars()
    dp.include_routers(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())


