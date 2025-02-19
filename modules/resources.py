import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy.orm import Session
from modules.db import Dbstruct
from modules.db import BotDb
from datetime import datetime
import io
import json

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


async def resource_autocomplete(interaction, current):
    results = session.query(Dbstruct.resources.resource_name).all()
    return [
        app_commands.Choice(name=name[0], value=name[0])
        for name in results
        if current.lower() in name[0].lower()
    ]


class ResourceManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="add_resource", description="أضف موردًا جديدًا")
    @app_commands.autocomplete(research=research_autocomplete)
    @app_commands.autocomplete(demand=demand_autocomplete)
    async def add_resource(
        self, interaction, title: str, research: str, demand: str, link: str
    ):
        research_obj: Dbstruct.research = (
            session.query(Dbstruct.research)
            .filter(Dbstruct.research.name == research)
            .first()
        )

        demand_entry: Dbstruct.demands = (
            session.query(Dbstruct.demands)
            .filter(
                Dbstruct.demands.research_id == research_obj.id,
                Dbstruct.demands.demand == demand,
            )
            .first()
        )

        new_resource = Dbstruct.resources(
            resource_name=f"{title} - {demand_entry.demand} ",
            resource_link=link,
            research_id=research_obj.id,
            demand_id=demand_entry.id,
            added_by=interaction.user.name,
        )

        session.add(new_resource)
        session.commit()

        embed = discord.Embed(
            title="✅ تمت الإضافة",
            description="تمت إضافة المورد بنجاح!",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="delete_resource", description="احذف موردًا")
    @app_commands.autocomplete(resource_id=resource_autocomplete)
    async def delete_resource(self, interaction, resource_id: int):

        resource = session.query(Dbstruct.resources).filter_by(id=resource_id).first()
        if resource:
            session.delete(resource)
            session.commit()
            embed = discord.Embed(
                title="🗑️ تم الحذف",
                description="تم حذف المورد بنجاح.",
                color=discord.Color.red(),
            )
        else:
            embed = discord.Embed(
                title="⚠️ خطأ",
                description="لم يتم العثور على المورد.",
                color=discord.Color.orange(),
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="show_resources", description="عرض الموارد المتوفرة")
    @app_commands.describe(
        research="Filter by research",
        demand="Filter by demand",
        export="Export as JSON file",
    )
    @app_commands.autocomplete(
        research=research_autocomplete, demand=demand_autocomplete
    )
    async def show_resources(
        self,
        interaction,
        research: str = None,
        demand: str = None,
        export: bool = False,
    ):
        query = session.query(Dbstruct.resources)
        if research:
            research_obj = (
                session.query(Dbstruct.research)
                .filter(Dbstruct.research.name == research)
                .first()
            )
            if research_obj:
                query = query.filter(Dbstruct.resources.research_id == research_obj.id)

        if demand:
            demand_obj = (
                session.query(Dbstruct.demands)
                .filter(Dbstruct.demands.demand == demand)
                .first()
            )
            if demand_obj:
                query = query.filter(Dbstruct.resources.demand_id == demand_obj.id)

        resources = query.all()

        if export:
            resources_data = [
                {
                    "Resource Name": res.resource_name,
                    "Link": res.resource_link,
                    "Added By": res.added_by,
                    "Status": "Read" if res.is_read else "Unread",
                    "Added At": (
                        res.added_at.strftime("%Y-%m-%d %H:%M:%S")
                        if res.added_at
                        else "Unknown"
                    ),
                }
                for res in resources
            ]
            json_bytes = io.BytesIO(
                json.dumps(resources_data, ensure_ascii=False, indent=4).encode("utf-8")
            )
            json_bytes.seek(0)
            await interaction.response.send_message(
                "📂 Exported resources as JSON.",
                file=discord.File(json_bytes, "resources.json"),
            )
            return

        if not resources:
            embed = discord.Embed(
                title="📚 Available Resources",
                description="No resources found.",
                color=discord.Color.orange(),
            )
        else:
            embed = discord.Embed(
                title="📂 Available Resources",
                description=f"Showing {len(resources)} resources.",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow(),
            )
            embed.set_thumbnail(
                url="https://media.tenor.com/LPXrrbFQKsoAAAAi/misinformation-fake-news.gif"
            )
            embed.set_footer(text="Resource Overview")

            for res in resources:
                status = "✅ Read" if res.is_read else "❌ Unread"
                embed.add_field(
                    name=f"🔹 {res.resource_name}",
                    value=(
                        f"🔗 **[Resource Link]({res.resource_link})**\n"
                        f"👤 **Added by:** {res.added_by}\n"
                        f"📖 **Status:** {status}\n"
                        "---------"
                    ),
                    inline=False,
                )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="mark_complete", description="وضع علامة كمكتمل")
    @app_commands.autocomplete(resource_id=resource_autocomplete)
    async def mark_complete(self, interaction, resource_id: int):

        resource = session.query(Dbstruct.resources).filter_by(id=resource_id).first()
        if resource:
            resource.is_read = True
            resource.read_by = interaction.user.name
            session.commit()
            embed = discord.Embed(
                title="✅ تم الإكمال",
                description=f"تم وضع علامة كمكتمل بواسطة {interaction.user.name}.",
                color=discord.Color.green(),
            )
        else:
            embed = discord.Embed(
                title="⚠️ خطأ",
                description="لم يتم العثور على المورد.",
                color=discord.Color.orange(),
            )

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.bot):
    await bot.add_cog(ResourceManagement(bot=bot))
