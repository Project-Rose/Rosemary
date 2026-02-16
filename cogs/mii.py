from discord.ext import commands
from random import choice, randint
import discord, aiohttp, base64, io, qrcode
from Crypto.Cipher import AES

# helper functions
def crc16(data: bytes):
    msb, lsb = 0, 0
    for byte in data:
        x = byte ^ msb
        x ^= (x >> 4)
        msb = (lsb ^ (x >> 3) ^ (x << 4)) & 0xFF
        lsb = (x ^ (x << 5)) & 0xFF
    return (msb << 8) + lsb

def encrypt_mii_data(data_bytes: bytearray):
    data_bytes[3] = 0x30
    nonce = data_bytes[12:20]
    content = data_bytes[0:12] + data_bytes[20:]
    checksum_content = data_bytes[0:12] + nonce + data_bytes[20:-2]
    new_crc = crc16(checksum_content)
    content = content[:-2] + bytes([(new_crc >> 8) & 0xFF, new_crc & 0xFF])
    key = bytes.fromhex("59FC817E6446EA6190347B20E9BDCE52")
    cipher = AES.new(key, AES.MODE_CCM, nonce=nonce + b'\x00\x00\x00\x00', mac_len=16)
    padded_content = content + b'\x00' * 8
    ciphertext, tag = cipher.encrypt_and_digest(padded_content)
    return nonce + ciphertext[:len(ciphertext)-8] + tag

class Mii(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.slash_command(description="Render a mii using mii-unsecure")
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
    @discord.option("pnid", description="The PNID of the Mii. Leave blank if using NNID.", required=False)
    @discord.option("nnid", description="The NNID of the Mii. Leave blank if using PNID.", required=False)
    async def mii(
        self,
        ctx: discord.ApplicationContext, 
        render: str, 
        expression: str, 
        type: str, 
        resolution: str, 
        clothes_color: str = None, 
        pants_color: str = None,
        pnid: str = None, 
        nnid: str = None
    ):
        nid = pnid or nnid
        api_id = 1 if pnid else 0

        if not nid or (pnid and nnid):
            return await ctx.respond("Please enter either a PNID or NNID, but not both.", ephemeral=True)

        await ctx.defer()

        shader_map = {"blinn": 3, "miitomo": 2, "switch": 1}
        shader_number = shader_map.get(render, 3)
        shader_type = "" if render == "wiiu" else f"&shaderType={shader_number}"

        image_url = f"https://mii-unsecure.ariankordi.net/miis/image.png?nnid={nid}&api_id={api_id}&type={type}&width={resolution}&expression={expression}{shader_type}"
        if clothes_color:
            image_url += f"&clothesColor={clothes_color}"
        if pants_color:
            image_url += f"&pantsColor={pants_color}"
        data_url = f"https://mii-unsecure.ariankordi.net/mii_data/{nid}?api_id={api_id}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as img_resp, session.get(data_url) as data_resp:
                    if img_resp.status != 200:
                        return await ctx.respond("The Mii could not be found!", ephemeral=True)
                
                    image_bytes = await img_resp.read()
                    mii_json = await data_resp.json()
            raw_mii_data = base64.b64decode(mii_json['data'])

            if clothes_color:
                # one by one because this is complicated
                # color table
                color_table = {"red": 0x00, "orange": 0x01, "yellow": 0x02, "yellowgreen": 0x03, "green": 0x04, "blue": 0x05, "skyblue": 0x06, "pink": 0x07, "purple": 0x08, "brown": 0x09, "white": 0x0A, "black": 0x0B}
                # we store the mii data in a bytesio object
                
                mii_data = io.BytesIO(raw_mii_data)
                # we go to 0x18, then we read 2 bytes, and we clear out the bits that contain the color (https://www.3dbrew.org/wiki/Mii#Mii_format)
                mii_data.seek(0x18)
                data = int.from_bytes(mii_data.read(2), byteorder="little") & 0xC3FF
                # we choose the new color, shift it by 10 and then we merge it with the rest with an OR operation
                new_color = color_table[clothes_color] << 10
                data = data | new_color
                # then we write the new data
                mii_data.seek(0x18)
                mii_data.write(data.to_bytes(2, byteorder="little"))
                # new checksum
                crc = crc16(mii_data.getvalue()[0:94])
                mii_data.seek(0x5E)
                mii_data.write(crc.to_bytes(2))
                
                mii_json['data'] = str(base64.b64encode(mii_data.getvalue()), encoding="utf-8")
                encrypted_data = encrypt_mii_data(bytearray(mii_data.getvalue()))

                mii_data.close()
            else:
                encrypted_data = encrypt_mii_data(bytearray(raw_mii_data))
            
            # Generate QR Code
            qr = qrcode.QRCode(border=1)
            qr.add_data(encrypted_data)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            qr_buffer = io.BytesIO()
            qr_img.save(qr_buffer, format="PNG")
            qr_buffer.seek(0)

            # Build Embed
            network_info = {
                "id_type": "PNID" if api_id == 1 else "NNID",
                "color": 0x1b1f3b if api_id == 1 else 0xFF7D00,
                "text": f"Environment: {'Pretendo' if api_id == 1 else 'Nintendo'} Network",
                "icon": "https://pretendo.network/assets/images/icons/favicon-32x32.png" if api_id == 1 else "https://media.discordapp.net/attachments/1290013025633304696/1295610730904817684/image.png"
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
            embed.add_field(name=network_info["id_type"], value=str(mii_json.get('user_id', nid)), inline=True)
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