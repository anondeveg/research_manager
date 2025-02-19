import discord
from discord import app_commands
from discord.ext import commands, tasks
from sqlalchemy.orm import Session
from modules.db import Dbstruct, BotDb
from modules.helper import create_embed
import datetime
import json
import io

session: Session = BotDb().session


async def research_autocomplete(
    interaction: discord.Interaction,
    current: str,
):
    results = session.query(Dbstruct.research.name).all()
    return [
        app_commands.Choice(name=name[0], value=name[0])
        for name in results
        if (current.lower() in name[0].lower() if current.lower() != "" else True)
    ]


async def demand_autocomplete(
    interaction: discord.Interaction,
    current: str,
):
    results = session.query(Dbstruct.demands.demand).all()
    return [
        app_commands.Choice(name=name[0], value=name[0])
        for name in results
        if current.lower() in name[0].lower()
    ]


class Demands(commands.Cog):
    """
    A Discord cog for searching and displaying Hadiths.


    Attributes:
        bot (discord.Client): The Discord bot instance.
    """

    def __init__(self, bot: discord.Client):
        self.bot = bot

    @app_commands.command(name="add_research")
    @app_commands.describe(research_name="the name of the research")
    @commands.has_permissions(administrator=True)
    async def add_research(self, interaction: discord.Interaction, research_name: str):
        await interaction.response.defer()

        # Add research to database
        research = Dbstruct.research(name=research_name)
        session.add(research)
        session.commit()

        # Create success embed
        embed = discord.Embed(
            title="✅ تم إضافة البحث بنجاح!",
            description=f"📚 البحث: **{research_name}**\n\nرائع! تم تسجيل البحث بنجاح في قاعدة البيانات. 🌟",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(
            url="https://media.tenor.com/-geUcjMXb8EAAAAj/yeahlee-ok-ok.gif"
        )
        embed.set_footer(
            text="نظام إدارة الأبحاث", icon_url=interaction.client.user.avatar.url
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="add_demand")
    @app_commands.describe(
        research="اسم البحث",
        demand="المطلب",
        researcher="الباحث المسؤول",
        deadline="تاريخ التسليم (التنسيق: YYYY-MM-DD HH:MM)",
    )
    @app_commands.autocomplete(research=research_autocomplete)
    @commands.has_permissions(administrator=False)
    async def add_demand(
        self,
        interaction: discord.Interaction,
        research: str,
        demand: str,
        researcher: discord.User = None,
        deadline: str = None,
    ):
        await interaction.response.defer()

        researcher_name = researcher.name if researcher else "غير محدد"

        try:
            if deadline:
                deadline_dt = datetime.datetime.strptime(deadline, "%Y-%m-%d %H:%M")
            else:
                deadline_dt = None
        except ValueError:
            embed = discord.Embed(
                title="❌ خطأ في إدخال التاريخ",
                description=(
                    "⚠️ الرجاء استخدام التنسيق الصحيح للتاريخ:\n"
                    "**`YYYY-MM-DD HH:MM`**"
                ),
                color=discord.Color.red(),
            )
            embed.set_footer(text="نظام إدارة الأبحاث")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        research_obj = (
            session.query(Dbstruct.research)
            .filter(Dbstruct.research.name == research)
            .first()
        )
        if not research_obj:
            embed = discord.Embed(
                title="❌ البحث غير موجود",
                description=("🔎 لم يتم العثور على بحث باسم:\n" f"**{research}**"),
                color=discord.Color.red(),
            )
            embed.set_footer(text="نظام إدارة الأبحاث")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # إضافة المطلب إلى قاعدة البيانات
        new_demand = Dbstruct.demands(
            demand=demand,
            added_by=interaction.user.name,
            researcher=researcher_name,
            research_id=research_obj.id,
            deadline=deadline_dt,
        )
        session.add(new_demand)
        session.commit()

        # إنشاء Embed للنجاح مع تنسيق مريح بصريًا
        embed = discord.Embed(
            title="✅ تم إضافة المطلب بنجاح!",
            description=(
                f"📌 **المطلب:**\n"
                f"➥ {demand}\n\n"
                f"📚 **البحث المرتبط:**\n"
                f"➥ {research}\n\n"
                f"🧑‍🔬 **الباحث المسؤول:**\n"
                f"➥ {researcher_name}\n\n"
                f"🗓️ **موعد التسليم:**\n"
                f"➥ {deadline_dt.strftime('%Y-%m-%d %H:%M') if deadline_dt else 'غير محدد'}"
            ),
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(
            url="https://media.tenor.com/-geUcjMXb8EAAAAj/yeahlee-ok-ok.gif"
        )
        embed.set_footer(
            text=f"تمت الإضافة بواسطة: {interaction.user.name}",
            icon_url=interaction.user.display_avatar.url,
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="assign_me")
    @app_commands.describe(research="اسم البحث", demand="المطلب")
    @app_commands.autocomplete(research=research_autocomplete)
    @app_commands.autocomplete(demand=demand_autocomplete)
    @commands.has_permissions(administrator=False)
    async def assign_me(
        self, interaction: discord.Interaction, research: str, demand: str
    ):
        await interaction.response.defer()

        research_obj = (
            session.query(Dbstruct.research)
            .filter(Dbstruct.research.name == research)
            .first()
        )

        if research_obj is None:
            embed = discord.Embed(
                title="❌ البحث غير موجود",
                description=("🔎 لم يتم العثور على بحث باسم:\n" f"**{research}**"),
                color=discord.Color.red(),
            )
            embed.set_footer(text="نظام إدارة الأبحاث")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        demand_entry = (
            session.query(Dbstruct.demands)
            .filter(
                Dbstruct.demands.research_id == research_obj.id,
                Dbstruct.demands.demand == demand,
            )
            .first()
        )

        if demand_entry is None:
            embed = discord.Embed(
                title="❌ المطلب غير موجود",
                description=(
                    "⚠️ لم يتم العثور على المطلب:\n"
                    f"**{demand}** ضمن البحث **{research}**"
                ),
                color=discord.Color.red(),
            )
            embed.set_footer(text="نظام إدارة الأبحاث")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # تحديث الباحث
        demand_entry.researcher = interaction.user.name
        session.commit()

        # إنشاء Embed للنجاح
        embed = discord.Embed(
            title="✅ تم تعيينك لهذا المطلب!",
            description=(
                f"📌 **المطلب:**\n"
                f"➥ {demand}\n\n"
                f"📚 **البحث المرتبط:**\n"
                f"➥ {research}\n\n"
                f"🧑‍🔬 **الباحث الحالي:**\n"
                f"➥ {interaction.user.name}"
            ),
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(
            url="https://media.tenor.com/-geUcjMXb8EAAAAj/yeahlee-ok-ok.gif"
        )
        embed.set_footer(
            text=f"تم التعيين بواسطة: {interaction.user.name}",
            icon_url=interaction.user.display_avatar.url,
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="edit_deadline")
    @app_commands.describe(
        research="اسم البحث",
        demand="المطلب المراد تعديل موعده",
        deadline="الموعد الجديد (التنسيق: YYYY-MM-DD HH:MM)",
    )
    @app_commands.autocomplete(research=research_autocomplete)
    @app_commands.autocomplete(demand=demand_autocomplete)
    @commands.has_permissions(administrator=True)
    async def edit_deadline(
        self,
        interaction: discord.Interaction,
        research: str,
        demand: str,
        deadline: str,
    ):
        await interaction.response.defer()

        # التحقق من تنسيق التاريخ
        try:
            deadline_dt = datetime.datetime.strptime(deadline, "%Y-%m-%d %H:%M")
        except ValueError:
            embed = discord.Embed(
                title="❌ خطأ في تنسيق التاريخ",
                description="الرجاء استخدام التنسيق التالي:\n**YYYY-MM-DD HH:MM**",
                color=discord.Color.red(),
            )
            embed.set_footer(text="نظام إدارة الأبحاث")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # البحث عن البحث المطلوب
        research_entry = (
            session.query(Dbstruct.research)
            .filter(Dbstruct.research.name == research)
            .first()
        )

        if not research_entry:
            embed = discord.Embed(
                title="❌ البحث غير موجود",
                description=f"لم يتم العثور على بحث باسم:\n**{research}**",
                color=discord.Color.red(),
            )
            embed.set_footer(text="نظام إدارة الأبحاث")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # البحث عن المطلب المطلوب
        demand_entry = (
            session.query(Dbstruct.demands)
            .filter(
                Dbstruct.demands.research_id == research_entry.id,
                Dbstruct.demands.demand == demand,
            )
            .first()
        )

        if not demand_entry:
            embed = discord.Embed(
                title="❌ المطلب غير موجود",
                description=f"لم يتم العثور على المطلب:\n**{demand}** ضمن البحث **{research}**",
                color=discord.Color.red(),
            )
            embed.set_footer(text="نظام إدارة الأبحاث")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # تحديث الموعد النهائي
        old_deadline = (
            demand_entry.deadline.strftime("%Y-%m-%d %H:%M")
            if demand_entry.deadline
            else "غير محدد"
        )
        demand_entry.deadline = deadline_dt
        session.commit()

        # إنشاء Embed للنجاح
        embed = discord.Embed(
            title="✅ تم تحديث موعد التسليم!",
            description=(
                f"📌 **المطلب:**\n➥ {demand}\n\n"
                f"📚 **البحث المرتبط:**\n➥ {research}\n\n"
                f"⏳ **الموعد القديم:**\n➥ {old_deadline}\n\n"
                f"🗓️ **الموعد الجديد:**\n➥ {deadline_dt.strftime('%Y-%m-%d %H:%M')}\n"
            ),
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(
            url="https://media.tenor.com/URUD0ndneQQAAAAi/approved-ok.gif"
        )
        embed.set_footer(
            text=f"تم التعديل بواسطة: {interaction.user.name}",
            icon_url=interaction.user.display_avatar.url,
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="remove_researcher")
    @app_commands.describe(
        research="اسم البحث", demand="المطلب الذي تريد إزالة الباحث منه"
    )
    @app_commands.autocomplete(research=research_autocomplete)
    @app_commands.autocomplete(demand=demand_autocomplete)
    @commands.has_permissions(administrator=True)
    async def remove_researcher(
        self, interaction: discord.Interaction, research: str, demand: str
    ):
        await interaction.response.defer()

        # البحث عن البحث
        research_entry = (
            session.query(Dbstruct.research)
            .filter(Dbstruct.research.name == research)
            .first()
        )

        if not research_entry:
            embed = discord.Embed(
                title="❌ البحث غير موجود",
                description=f"لم يتم العثور على بحث باسم:\n**{research}**",
                color=discord.Color.red(),
            )
            embed.set_footer(text="نظام إدارة الأبحاث")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # البحث عن المطلب
        demand_entry = (
            session.query(Dbstruct.demands)
            .filter(
                Dbstruct.demands.research_id == research_entry.id,
                Dbstruct.demands.demand == demand,
            )
            .first()
        )

        if not demand_entry:
            embed = discord.Embed(
                title="❌ المطلب غير موجود",
                description=f"لم يتم العثور على المطلب:\n**{demand}** ضمن البحث **{research}**",
                color=discord.Color.red(),
            )
            embed.set_footer(text="نظام إدارة الأبحاث")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # التحقق من وجود باحث معين
        if demand_entry.researcher is None:
            embed = discord.Embed(
                title="⚠️ لا يوجد باحث معين",
                description=f"لا يوجد حاليًا باحث مسند لهذا المطلب:\n**{demand}**",
                color=discord.Color.yellow(),
            )
            embed.set_footer(text="نظام إدارة الأبحاث")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # إزالة الباحث
        old_researcher = demand_entry.researcher
        demand_entry.researcher = None
        session.commit()

        # إنشاء Embed للنجاح
        embed = discord.Embed(
            title="✅ تم إزالة الباحث بنجاح!",
            description=(
                f"📚 **البحث:**\n➥ {research}\n\n"
                f"📌 **المطلب:**\n➥ {demand}\n\n"
                f"🧑‍🔬 **الباحث السابق:**\n➥ {old_researcher}\n"
            ),
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(
            url="https://media.tenor.com/8QWQ1lWBg04AAAAi/remove-trash-bin.gif"
        )
        embed.set_footer(
            text=f"تم التعديل بواسطة: {interaction.user.name}",
            icon_url=interaction.user.display_avatar.url,
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="show_demands")
    @app_commands.describe(
        research="The name of the research",
        export="Set to True to export demands as a JSON file",
    )
    @app_commands.autocomplete(research=research_autocomplete)
    @commands.has_permissions(administrator=False)
    async def show_demands(
        self,
        interaction: discord.Interaction,
        research: str,
        export: bool = False,  # Optional parameter
    ):
        await interaction.response.defer()

        # Find the research
        research_entry = (
            session.query(Dbstruct.research)
            .filter(Dbstruct.research.name == research)
            .first()
        )

        if not research_entry:
            await interaction.followup.send("❌ Research not found.", ephemeral=True)
            return

        # Get all demands for the research
        demands = (
            session.query(Dbstruct.demands)
            .filter(Dbstruct.demands.research_id == research_entry.id)
            .all()
        )

        if not demands:
            await interaction.followup.send(
                f"📭 No demands found for research `{research}`.", ephemeral=True
            )
            return

        if export:
            # Convert demands to JSON
            demands_list = [
                {
                    "demand": demand.demand,
                    "added_by": demand.added_by,
                    "researcher": demand.researcher,
                    "deadline": (
                        demand.deadline.strftime("%Y-%m-%d %H:%M")
                        if demand.deadline
                        else "No Deadline"
                    ),
                    "status": (
                        "In Progress" if demand.researcher != "غير محدد" else "Pending"
                    ),
                }
                for demand in demands
            ]

            json_data = json.dumps(demands_list, indent=4, ensure_ascii=False)

            # Use BytesIO instead of writing to a file
            json_bytes = io.BytesIO(json_data.encode("utf-8"))
            json_bytes.seek(0)

            file_name = f"{research}_demands.json"
            await interaction.followup.send(
                file=discord.File(json_bytes, filename=file_name)
            )
            return

        # Create embed if JSON export is not requested
        embed = discord.Embed(
            title=f"📂 Demands for Research: {research}",
            description=f"Showing {len(demands)} demands.",
            color=discord.Color.purple(),
            timestamp=datetime.datetime.utcnow(),
        )

        embed.set_thumbnail(
            url="https://cdn-icons-png.flaticon.com/512/1246/1246261.png"
        )
        embed.set_footer(text="Research Demands Overview")

        for demand in demands:
            deadline_str = (
                demand.deadline.strftime("%Y-%m-%d %H:%M")
                if demand.deadline
                else "No Deadline"
            )
            researcher_str = (
                demand.researcher if demand.researcher != "غير محدد" else False
            )
            status = "🟢" if researcher_str else "🟡 Pending (waiting for researcher)"

            done = "🟢" if demand.done == True else "🔴"
            embed.add_field(
                name=f"🔹 {demand.demand}",
                value=(
                    f"**Added by:** {demand.added_by}\n"
                    f"**Researcher:** {str(demand.researcher)}\n"
                    f"**Deadline:** {deadline_str}\n"
                    f"**Status:** {status}\n"
                    f"**Done?**: {done}"
                ),
                inline=False,
            )

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="mark_demand_done")
    @app_commands.describe(research="اسم البحث", demand="المطلب المراد تعيينه كمكتمل")
    @app_commands.autocomplete(research=research_autocomplete)
    @app_commands.autocomplete(demand=demand_autocomplete)
    @commands.has_permissions(administrator=False)
    async def mark_demand_done(
        self, interaction: discord.Interaction, research: str, demand: str
    ):
        await interaction.response.defer()

        # البحث عن البحث المطلوب
        research_entry = (
            session.query(Dbstruct.research)
            .filter(Dbstruct.research.name == research)
            .first()
        )

        if not research_entry:
            embed = discord.Embed(
                title="❌ البحث غير موجود",
                description=f"لم يتم العثور على بحث باسم:\n**{research}**",
                color=discord.Color.red(),
            )
            embed.set_footer(text="نظام إدارة الأبحاث")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # البحث عن المطلب المطلوب
        demand_entry = (
            session.query(Dbstruct.demands)
            .filter(
                Dbstruct.demands.research_id == research_entry.id,
                Dbstruct.demands.demand == demand,
            )
            .first()
        )

        if not demand_entry:
            embed = discord.Embed(
                title="❌ المطلب غير موجود",
                description=f"لم يتم العثور على المطلب:\n**{demand}** ضمن البحث **{research}**",
                color=discord.Color.red(),
            )
            embed.set_footer(text="نظام إدارة الأبحاث")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # تحديث الحالة إلى مكتمل
        demand_entry.done = True
        session.commit()

        # إنشاء Embed للنجاح
        embed = discord.Embed(
            title="✅ تم تعيين المطلب كمكتمل!",
            description=(
                f"📚 **البحث:**\n➥ {research}\n\n"
                f"📌 **المطلب:**\n➥ {demand}\n\n"
                f"🎉 **الحالة:**\n✅ مكتمل"
            ),
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(url="https://media1.tenor.com/m/s50cn0tfWewAAAAC/cat.gif")
        embed.set_footer(
            text=f"تم التعديل بواسطة: {interaction.user.name}",
            icon_url=interaction.user.display_avatar.url,
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="mark_demand_undone")
    @app_commands.describe(
        research="اسم البحث", demand="المطلب المراد تعيينه كغير مكتمل"
    )
    @app_commands.autocomplete(research=research_autocomplete)
    @app_commands.autocomplete(demand=demand_autocomplete)
    @commands.has_permissions(administrator=False)
    async def mark_demand_undone(
        self, interaction: discord.Interaction, research: str, demand: str
    ):
        await interaction.response.defer()

        # البحث عن البحث المطلوب
        research_entry = (
            session.query(Dbstruct.research)
            .filter(Dbstruct.research.name == research)
            .first()
        )

        if not research_entry:
            embed = discord.Embed(
                title="❌ البحث غير موجود",
                description=f"لم يتم العثور على بحث باسم:\n**{research}**",
                color=discord.Color.red(),
            )
            embed.set_footer(text="نظام إدارة الأبحاث")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # البحث عن المطلب المطلوب
        demand_entry = (
            session.query(Dbstruct.demands)
            .filter(
                Dbstruct.demands.research_id == research_entry.id,
                Dbstruct.demands.demand == demand,
            )
            .first()
        )

        if not demand_entry:
            embed = discord.Embed(
                title="❌ المطلب غير موجود",
                description=f"لم يتم العثور على المطلب:\n**{demand}** ضمن البحث **{research}**",
                color=discord.Color.red(),
            )
            embed.set_footer(text="نظام إدارة الأبحاث")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # تحديث الحالة إلى غير مكتمل
        demand_entry.done = False
        session.commit()

        # إنشاء Embed للنجاح
        embed = discord.Embed(
            title="❌ تم تعيين المطلب كغير مكتمل!",
            description=(
                f"📚 **البحث:**\n➥ {research}\n\n"
                f"📌 **المطلب:**\n➥ {demand}\n\n"
                f"⏳ **الحالة:**\n❌ غير مكتمل"
            ),
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(
            url="https://media1.tenor.com/m/0QkZnCmGFX0AAAAC/banana-cat-banana-cat-crying.gif"
        )
        embed.set_footer(
            text=f"تم التعديل بواسطة: {interaction.user.name}",
            icon_url=interaction.user.display_avatar.url,
        )

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.bot):
    """
    Setup function for adding the Auth cog to the bot.

    Args:
        bot (commands.Bot): The Discord bot instance.

    Returns:
        None
    """
    await bot.add_cog(Demands(bot=bot))
