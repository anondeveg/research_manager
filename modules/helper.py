import discord


async def create_embed(title: str, content: str, color: discord.Color):
    """
    Create and return a Discord embed with the specified title, content, and color.

    Args:
        title (str): The title of the embed.
        content (str): The content of the embed.
        color (discord.Color): The color of the embed.

    Returns:
        discord.Embed: The created embed.
    """
    embed = discord.Embed(title=title, color=color)
    embed.add_field(name=content, value="")
    embed.set_footer(text="if you think something is wrong, please open a ticket")
    return embed
