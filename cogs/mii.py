from Crypto.Cipher import AES
from discord.ext import commands
import discord
import io
import base64
import qrcode
import aiohttp
import os

# helper functions
def crc16_ccitt(data: bytearray):
    """
    Calculates the CRC-16/CCITT/XMODEM checksum for the specified input data.
    Courtesy of Luciano Barcaro: https://stackoverflow.com/a/30357446
    """
    msb, lsb = 0, 0
    for c in data:
        x = c ^ msb
        x ^= (x >> 4)
        msb = (lsb ^ (x >> 3) ^ (x << 4)) & 255
        lsb = (x ^ (x << 5)) & 255
    return (msb << 8) + lsb

qr_code_key = bytes.fromhex("59FC817E6446EA6190347B20E9BDCE52")

def encrypt_mii_data_for_qr_code(data: bytearray, key: bytes) -> bytes:
    """
    Encrypt 3DS/Wii U Mii StoreData (96 bytes) into QR code wrapped format (112 bytes).
    Retrieved from: https://jsfiddle.net/arian_/ckya346z/19/

    :param data: Input 96-byte StoreData (Ver3StoreData).
    :param key: AES key (16 bytes).
    :raises ValueError: if data length is not 96 bytes.
    """

    VER3_STORE_DATA_LENGTH = 96   # 3DS/Wii U Mii StoreData
    ID_OFFSET = 12        # Offset of CreateID in StoreData
    ID_LENGTH = 8         # Length of CreateID used for nonce
    TAG_LENGTH = 16       # AES-CCM tag length
    NONCE_LENGTH = 12     # AES-CCM nonce length

    if len(data) != VER3_STORE_DATA_LENGTH:
        raise ValueError(f"encrypt_aes_ccm: Input size is {len(data)}, expected {VER3_STORE_DATA_LENGTH}")

    # The ID to include in the encrypted data as the nonce (IV).
    id_end_offset = ID_OFFSET + ID_LENGTH
    id = bytes(data[ID_OFFSET:id_end_offset])

    # Content to be encrypted: data with ID cut out, padded with 8 zeros.
    content = bytearray(VER3_STORE_DATA_LENGTH)
    content[0:ID_OFFSET] = data[0:ID_OFFSET]
    content[ID_OFFSET:] = data[id_end_offset:]

    # AES-CCM nonce initialized to zeroes with ID at the start.
    nonce = bytearray(NONCE_LENGTH)
    nonce[0:ID_LENGTH] = id

    # Encrypt the padded content using the ID as nonce (IV).
    cipher = AES.new(key, AES.MODE_CCM, nonce=bytes(nonce), mac_len=TAG_LENGTH)
    encrypted_bytes = cipher.encrypt(bytes(content))
    tag = cipher.digest()

    # Construct result: nonce + encrypted content + tag.
    result = id + encrypted_bytes + tag
    return result

# Reference for 3DS/Wii U format Mii data: https://github.com/Genwald/MiiPort/blob/4ee38bbb8aa68a2365e9c48d59d7709f760f9b5d/include/mii_ext.h#L170-L264
def update_mii_checksum(mii_data):
    """
    Update the checksum and set Mii properties to make it friendly for QR scanning.
    """
    # Set birthPlatform bitfield to 3 (CFLi_BIRTH_PLATFORM_CTR).
    mii_data[3] = mii_data[3] & 0b10001111 | 0b00110000
    # Allow the Mii to be copied, for convenience.
    mii_data[1] |= 1 # copyable = 1

    # calculate and write new crc16 checksum
    crc = crc16_ccitt(mii_data[0:94])
    # set uint16 number
    mii_data[94] = (crc >> 8) & 0xFF
    mii_data[95] = crc & 0xFF

def set_favorite_color(mii_data: bytearray, favorite_color):
    # set favoriteColor bitfield
    mii_data[0x19] = mii_data[0x19] & 0xc3 | (favorite_color & 0xf) * 4

def make_mii_qr_code(raw_mii_data: bytearray, favorite_color: int|None = None) -> io.BytesIO:
    if favorite_color is not None: # only set clothes color if value is not None
        set_favorite_color(raw_mii_data, favorite_color)

    update_mii_checksum(raw_mii_data)
    encrypted_data = encrypt_mii_data_for_qr_code(raw_mii_data, qr_code_key)

    # Generate QR Code
    qr = qrcode.QRCode(version=5, border=1)
    qr.add_data(bytes(encrypted_data))
    qr_img = qr.make_image(fill_color="black", back_color="white")

    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    return qr_buffer

# main routine

rendering_endpoint = os.getenv("RENDERING_ENDPOINT")
nnid_lookup_endpoint = os.getenv("NNID_LOOKUP_ENDPOINT")

class Mii(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.Bot = bot

    @commands.slash_command(description="Render a Mii with Arian's Mii Renderer REAL")
    @discord.option("render", description="Select the render style", choices=[
        discord.OptionChoice("Wii U/Miiverse", "wiiu"),
        discord.OptionChoice("Switch", "switch"),
        discord.OptionChoice("Miitomo", "miitomo"),
        discord.OptionChoice("Blinn (Wii Kareoke U render)", "blinn")
    ])
    @discord.option("expression", description="Select the expression", choices=[
        discord.OptionChoice("Normal", "normal"),
        discord.OptionChoice("Smile", "smile"),
        discord.OptionChoice("Anger", "anger"),
        discord.OptionChoice("Sorrow", "sorrow"),
        discord.OptionChoice("Surprise", "surprise"),
        discord.OptionChoice("Blink", "blink"),
        discord.OptionChoice("Normal (open mouth)", "normal_open_mouth"),
        discord.OptionChoice("Smile (open mouth)", "smile_open_mouth"),
        discord.OptionChoice("Anger (open mouth)", "anger_open_mouth"),
        discord.OptionChoice("Surprise (open mouth)", "surprise_open_mouth"),
        discord.OptionChoice("Sorrow (open mouth)", "sorrow_open_mouth"),
        discord.OptionChoice("Blink (open mouth)", "blink_open_mouth"),
        discord.OptionChoice("Wink (left eye open)", "wink_left"),
        discord.OptionChoice("Wink (right eye open)", "wink_right"),
        discord.OptionChoice("Wink (left eye and mouth open)", "wink_left_open_mouth"),
        discord.OptionChoice("Wink (right eye and mouth open)", "wink_right_open_mouth"),
        discord.OptionChoice("Wink (left eye open and smiling)", "like_wink_left"),
        discord.OptionChoice("Wink (right eye open and smiling)", "like_wink_right"),
        discord.OptionChoice("Frustrated", "frustrated")
    ])
    @discord.option("type", description="Select positioning", choices=[
        discord.OptionChoice("Portrait", "face"),
        discord.OptionChoice("Head Only", "face_only"),
        discord.OptionChoice("Head Only Alt", "fflmakeicon"),
        discord.OptionChoice("Whole Body", "all_body"),
        discord.OptionChoice("Switch Portrait", "variableiconbody")
    ])
    @discord.option("resolution", description="Resolution of the rendered image", choices=[
        discord.OptionChoice("0.35x (96px, like mii-secure)", "96"),
        discord.OptionChoice("1x (270px)", "270"),
        discord.OptionChoice("2x (540px)", "540"),
        discord.OptionChoice("3x (810px)", "810"),
        discord.OptionChoice("4x (1080px)", "1080")
    ])
    @discord.option("clothes_color", description="Override the color of the clothes", choices=[
        discord.OptionChoice("Red", "red"),
        discord.OptionChoice("Orange", "orange"),
        discord.OptionChoice("Yellow", "yellow"),
        discord.OptionChoice("Light green", "yellowgreen"),
        discord.OptionChoice("Dark green", "green"),
        discord.OptionChoice("Dark blue", "blue"),
        discord.OptionChoice("Light blue", "skyblue"),
        discord.OptionChoice("Pink", "pink"),
        discord.OptionChoice("Purple", "purple"),
        discord.OptionChoice("Brown", "brown"),
        discord.OptionChoice("White", "white"),
        discord.OptionChoice("Black", "black")
    ], required=False)
    @discord.option("pants_color", description="(Only affects the render!) Override the color of the pants", choices=[
        discord.OptionChoice("Gray", "gray"),
        discord.OptionChoice("Red", "red"),
        discord.OptionChoice("Dark blue", "blue"),
        discord.OptionChoice("Gold", "gold")
    ], required=False)
    @discord.option("pnid", description="Pretendo Network ID to get the Mii from. Leave blank if using NNID.", required=False)
    @discord.option("nnid", description="Nintendo Network ID to get the Mii from. Leave blank if using PNID.", required=False)
    async def mii(
        self,
        ctx: discord.ApplicationContext,
        render: str,
        expression: str,
        type: str,
        resolution: str,
        clothes_color: str|None = None,
        pants_color: str|None = None,
        pnid: str|None = None,
        nnid: str|None = None
    ):
        nnas_id = pnid or nnid
        # 1 = pretendo, 0 = nintendo
        api_id = 1 if pnid else 0

        if not nnas_id or (pnid and nnid):
            return await ctx.respond("Please enter either a PNID or NNID, but not both.", ephemeral=True)

        await ctx.defer()

        # https://github.com/ariankordi/FFL-Testing/blob/renderer-server-prototype/server-impl/ffl-testing-web-server.go
        shader_map = {"blinn": 3, "miitomo": 2, "switch": 1}
        shader_number = shader_map.get(render, 3)
        shader_type = "" if render == "wiiu" else f"&shaderType={shader_number}"

        image_url = f"{rendering_endpoint}?nnid={nnas_id}&api_id={api_id}&type={type}&width={resolution}&expression={expression}{shader_type}"
        if clothes_color:
            image_url += f"&clothesColor={clothes_color}"
        if pants_color:
            image_url += f"&pantsColor={pants_color}"
        data_url = f"{nnid_lookup_endpoint}?nnid={nnas_id}&api_id={api_id}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as img_resp, session.get(data_url) as data_resp:
                    if img_resp.status != 200:
                        return await ctx.respond("The Mii could not be found!", ephemeral=True)

                    image_bytes = await img_resp.read()
                    mii_json = await data_resp.json()
            raw_mii_data = bytearray(base64.b64decode(mii_json['data']))

            # the index is the name of the color, e.g. black = 11
            favorite_color_string_table = [ "red", "orange", "yellow", "yellowgreen", "green", "blue", "skyblue", "pink", "purple", "brown", "white", "black"]
            favorite_color_int = None
            if clothes_color: # if clothes color is specified, parse from string
                favorite_color_int = favorite_color_string_table.index(clothes_color)

            qr_buffer = make_mii_qr_code(raw_mii_data, favorite_color_int)

            # Build Embed
            env_name = 'Pretendo' if api_id == 1 else 'Nintendo'
            pn_icon = "https://pretendo.network/assets/images/icons/favicon-32x32.png"
            nn_icon = "https://media.discordapp.net/attachments/1290013025633304696/1295610730904817684/image.png"
            network_info = {
                "id_type": "PNID" if api_id == 1 else "NNID",
                "color": 0x1b1f3b if api_id == 1 else 0xFF7D00,
                "text": f"Environment: {env_name} Network",
                "icon": pn_icon if api_id == 1 else nn_icon
            }

            embed = discord.Embed(
                title=f"{mii_json.get('name', 'Unknown')}'s Mii",
                description="Here are the details for your Mii.",
                color=network_info["color"]
            )
            embed.set_thumbnail(url="attachment://mii.png")
            embed.set_image(url="attachment://mii_qr.png")
            embed.set_footer(text=network_info["text"], icon_url=network_info["icon"])

            embed.add_field(name="Name", value=mii_json.get('name', 'N/A'), inline=True)
            embed.add_field(name=network_info["id_type"], value=str(mii_json.get('user_id', nnas_id)), inline=True)
            embed.add_field(name="Mii data (base64)", value=mii_json["data"], inline=False)
            embed.add_field(name="QR Code:", value="\u200B", inline=False)

            mii_file = discord.File(io.BytesIO(image_bytes), filename="mii.png")
            qr_file = discord.File(qr_buffer, filename="mii_qr.png")

            await ctx.respond(embed=embed, files=[mii_file, qr_file])
        except Exception as e:
            print(f"Error fetching Mii: {e}")
            await ctx.respond("Couldn't fetch your Mii. Please try again.", ephemeral=True)

def setup(bot):
    bot.add_cog(Mii(bot))
