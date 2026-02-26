import logging

from aiogram import Bot, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_ID
from database import get_tournament_by_cid, mark_published
from poster import load_venues, format_post, publish_to_group

logger = logging.getLogger(__name__)

router = Router()


class TournamentPublish(StatesGroup):
    waiting_venue = State()
    waiting_description = State()
    waiting_confirmation = State()


async def notify_admin_new_tournament(bot: Bot, tournament: dict):
    """Send notification to admin about a new tournament."""
    location = tournament.get("location", "")
    location_line = f"📍 {location}\n" if location else ""
    source = tournament.get("source", "padelteams")
    source_label = "tiepadel.com" if source == "tiepadel" else "padelteams.pt"
    text = (
        f"🏆 <b>Новый турнир!</b> ({source_label})\n\n"
        f"<b>{tournament['name']}</b>\n"
        f"📅 {tournament['dates']}\n"
        f"{location_line}\n"
        f"🔗 {tournament['tournament_url']}\n\n"
        f"Нажмите кнопку, чтобы начать публикацию."
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📝 Опубликовать",
            callback_data=f"publish:{tournament['key']}",
        )]
    ])
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=text,
        parse_mode="HTML",
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("publish:"))
async def on_publish_start(callback: CallbackQuery, state: FSMContext):
    """Admin clicked 'Publish' — show venue selection."""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return

    key = callback.data.split(":", 1)[1]
    tournament = await get_tournament_by_cid(key)
    if not tournament:
        await callback.answer("Турнир не найден в базе", show_alert=True)
        return

    await state.update_data(tournament_key=key)
    venues = load_venues()

    if not venues:
        await callback.message.answer("⚠️ Файл venues.txt пуст. Добавьте площадки.")
        await callback.answer()
        return

    buttons = []
    for i, venue in enumerate(venues):
        buttons.append([InlineKeyboardButton(
            text=venue["name"],
            callback_data=f"venue:{i}",
        )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer(
        f"📍 Выберите место проведения для <b>{tournament['name']}</b>:",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await state.set_state(TournamentPublish.waiting_venue)
    await callback.answer()


@router.callback_query(TournamentPublish.waiting_venue, F.data.startswith("venue:"))
async def on_venue_selected(callback: CallbackQuery, state: FSMContext):
    """Admin selected a venue — ask for description."""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return

    venue_idx = int(callback.data.split(":", 1)[1])
    venues = load_venues()

    if venue_idx >= len(venues):
        await callback.answer("Некорректный выбор", show_alert=True)
        return

    venue = venues[venue_idx]
    await state.update_data(venue=venue)

    await callback.message.answer(
        f"✅ Площадка: <b>{venue['name']}</b>\n\n"
        f"Теперь отправьте описание турнира (текст сообщения):",
        parse_mode="HTML",
    )
    await state.set_state(TournamentPublish.waiting_description)
    await callback.answer()


@router.message(TournamentPublish.waiting_description, F.from_user.id == ADMIN_ID)
async def on_description_received(message: Message, state: FSMContext):
    """Admin sent description — show preview and ask for confirmation."""
    description = message.text or ""
    data = await state.get_data()
    tournament = await get_tournament_by_cid(data["tournament_key"])
    venue = data["venue"]

    if not tournament:
        await message.answer("⚠️ Турнир не найден в базе.")
        await state.clear()
        return

    await state.update_data(description=description)

    preview = format_post(tournament, venue, description)
    await message.answer(
        f"👁 <b>Превью поста:</b>\n\n{preview}",
        parse_mode="HTML",
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Опубликовать", callback_data="confirm:yes"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="confirm:no"),
        ]
    ])
    await message.answer("Опубликовать в группу?", reply_markup=keyboard)
    await state.set_state(TournamentPublish.waiting_confirmation)


@router.callback_query(TournamentPublish.waiting_confirmation, F.data.startswith("confirm:"))
async def on_confirmation(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Admin confirmed or cancelled publication."""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return

    choice = callback.data.split(":", 1)[1]

    if choice == "no":
        await callback.message.answer("❌ Публикация отменена.")
        await state.clear()
        await callback.answer()
        return

    data = await state.get_data()
    tournament = await get_tournament_by_cid(data["tournament_key"])
    venue = data["venue"]
    description = data.get("description", "")

    if not tournament:
        await callback.message.answer("⚠️ Турнир не найден в базе.")
        await state.clear()
        await callback.answer()
        return

    try:
        await publish_to_group(bot, tournament, venue, description)
        await mark_published(tournament["cid"])
        await callback.message.answer("✅ Пост опубликован в группу!")
    except Exception as e:
        logger.exception("Failed to publish post")
        await callback.message.answer(f"⚠️ Ошибка публикации: {e}")

    await state.clear()
    await callback.answer()
