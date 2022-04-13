from telegram import (
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove, Update,
    InlineKeyboardButton, InlineKeyboardMarkup
)

from datetime import datetime
import pytz


from telegram.ext import (
    CommandHandler, CallbackContext,
    ConversationHandler, MessageHandler,
    Filters, Updater, CallbackQueryHandler
)


from config import (
    api_key, #sender_email,
    api_secret,
    FAUNA_KEY
)


import cloudinary
from cloudinary.uploader import upload
from faunadb import query as q
from faunadb.client import FaunaClient
from faunadb.errors import NotFound


# configure cloudinary
cloudinary.config(
    cloud_name="studentstore",
    api_key=api_key,
    api_secret=api_secret
)

# fauna client config
client = FaunaClient(secret=FAUNA_KEY)
tz_BISH = pytz.timezone('Asia/Bishkek') 
datetime_NY = datetime.now(tz_BISH)

# Define Options
SELL_OR_BUY, CHOOSING, CLASS_STATE, SME_DETAILS, CHOOSE_PREF, SEARCH,\
    SME_CAT, ADD_PRODUCTS, SME_CATALOGUE, POST_VIEW_CATALOGUE,\
         SHOW_STOCKS, POST_VIEW_PRODUCTS = range(12)

# inital options
reply_keyboard = [
    [
        InlineKeyboardButton(
            text="Seller",
            callback_data="SME"
        ),
        InlineKeyboardButton(
            text="Customer",
            callback_data="Customer"
        )
    ]
]
markup = InlineKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

# client.query(
#             q.update(
#                 q.ref(
#                     q.collection('User'), user['ref'].id()
#                 ),
#                 {'data': {'is_smeowner': False}}
#             )
#         )

def start(update, context: CallbackContext) -> int:
    # print("start here")
    bot = context.bot
    chat_id = update.message.chat.id
    # Check if user already exists before creating new user
    try:
        _user = client.query(
            q.get(
                q.match(
                    q.index("user_by_chat_id"),
                    chat_id
                )
            )
        )
        # print(_user)
        if _user != None:
            print(datetime_NY.strftime("%H:%M:%S"), '\t', chat_id, '\t| User |\t', _user['data']['name'])
            context.user_data["user-name"] = _user['data']['name'].strip().lower()
            context.user_data["user-id"] = _user["ref"].id()
            button = [
                [
                    InlineKeyboardButton(
                        text="Buy",
                        callback_data="customer"
                    )
                ,
                
                    InlineKeyboardButton(
                        text="Sell",
                        callback_data="sme"
                    )
                ],
              [
                InlineKeyboardButton(
                        text="Exit",
                        callback_data="exit"
                    )
              ]
            ]
            _markup = InlineKeyboardMarkup(
                button,
                one_time_keyboard=True
            )
            bot.send_message(
                chat_id=chat_id,
                text="What would you like to do?",
                reply_markup=_markup
            )
            return SELL_OR_BUY
    except NotFound:
        bot.send_message(
            chat_id=chat_id,
            text= "Hey there 👋"
        )
        bot.send_message(
            chat_id=chat_id,
            text= "Please provide your full name and mobile number, "
          "separated by comma\ne.g: "
          " John Doe, +9965553549"
        )
        return CHOOSING
      

def after_start(update, context: CallbackContext) -> int:
    # print("You called")
    bot = context.bot
    chat_id = update.callback_query.message.chat.id
    # print(chat_id)
    # print(update.callback_query.data)
    user = client.query(
            q.get(
                q.match(
                    q.index('user_by_name'), 
                    context.user_data['user-name'].strip().lower()
                )
            )
        )
    # Check if user wants to buy or sell 
    if update.callback_query.data.lower() == "exit":
        bot.send_message(
            chat_id=chat_id,
            text="Bye! Hope to see you soon!"
        )
        return ConversationHandler.END
      
    elif (update.callback_query.data.lower() == "customer") or (update.callback_query.data.lower() == "customer_back"):
        client.query(
            q.update(
                q.ref(
                    q.collection('User'), user['ref'].id()
                ),
                {'data': {'is_smeowner': False}}
            )
        )
        context.user_data["user-id"] = user["ref"].id()
        context.user_data["user-name"] = user['data']['name'].lower().strip()
        context.user_data['user-data'] = user['data']
        button = [
            [
                InlineKeyboardButton(
                    text="View vendors to buy from",
                    callback_data="customer"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Search for a vendor by name",
                    callback_data="customer;search"
                )
            ],
          [
                InlineKeyboardButton(
                    text="Exit",
                    callback_data="exit"
                )
            ]
        ]
        bot.send_message(
            chat_id=chat_id,
            text=f"Welcome back {user['data']['name'].split(' ')[0].capitalize()}!",
            reply_markup=InlineKeyboardMarkup(button)
        )
        return CLASS_STATE
    else:
        client.query(
            q.update(
                q.ref(
                    q.collection('User'), user['ref'].id()
                ),
                {'data': {'is_smeowner': True}}
            )
        )
        try:
            sme = client.query(
                        q.get(
                            q.match(
                                q.index("business_by_chat_id"),
                                chat_id
                            )
                        )
                    )
            if sme:
                context.user_data["sme_name"] = sme['data']['name'].lower().strip()
                context.user_data['sme_cat'] = sme['data']['category'].lower().strip()
                context.user_data['sme_id'] = sme['ref'].id()
                # context.user_data['sme_link'] = sme['data']['business_link']
                button = [
                    [
                        InlineKeyboardButton(
                            text="Add A New Product",
                            callback_data=chat_id
                        ),
                        InlineKeyboardButton(
                            text="View your catalogue",
                            callback_data="catalogue"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="Exit",
                            callback_data="exit"
                        )
                    ]
                ]
                _markup = InlineKeyboardMarkup(
                    button,
                    one_time_keyboard=True
                )
                bot.send_message(
                    chat_id=chat_id,
                    text=f"Welcome back {user['data']['name'].split(' ')[0].capitalize()}!",
                    reply_markup=_markup
                )
                return ADD_PRODUCTS
        
        except NotFound:
            return CLASS_STATE
          
          
def choose(update, context):
    bot = context.bot
    chat_id = update.message.chat.id
    # create new data entry
    data = update.message.text.split(',')
    if len(data) < 2 or len(data) > 2:
        bot.send_message(chat_id=chat_id, text="Invalid entry!")
        bot.send_message(chat_id=chat_id, text="Type /start, to restart bot"
)
        return ConversationHandler.END
    #TODO: Check if user already exists before creating new user
    new_user = client.query(q.create(q.collection('User'), {
            "data":{
                "name":data[0].strip().lower(),
                "whatsapp":data[1].strip(),
                "is_smeowner": False,
                "preference": "",
                "chat_id": chat_id
            }
        })
    )
    context.user_data["user-id"] = new_user["ref"].id()
    context.user_data["user-name"] = data[0].strip().lower()
    context.user_data['user-data'] = new_user['data']
  
    bot.send_message(
        chat_id=chat_id,
        text="🎉🎉🎉\nThank you!\n"
        "Which of the following do you identify as?",
        reply_markup=markup
    )
    return CLASS_STATE

def classer(update, context):
    bot = context.bot
    chat_id = update.callback_query.message.chat.id
    name = context.user_data["user-name"].lower().strip()
    # print('Inside Classer - ', update.callback_query.data.lower())
    if update.callback_query.data.lower() == "exit":
      return SELL_OR_BUY
    elif update.callback_query.data.lower() == "sme":
        # update user as smeowner
        client.query(
            q.update(
                q.ref(q.collection("User"), context.user_data["user-id"]),
                {"data": {"is_smeowner":True}}
            )
        )
        bot.send_message(
            chat_id=chat_id,
            text=f"Great!\n{name.split(' ')[0]},"
            " please provide your BrandName/Name, Room Number and WhatsApp number separated by comma (,)\n"
            "e.g: Jonny, A12, +234567897809",
            reply_markup=ReplyKeyboardRemove()
        )

        return SME_DETAILS
    categories = [  
        [
            InlineKeyboardButton(
                text="Food",
                callback_data="Food"
            ),
            InlineKeyboardButton(
                text="Other",
                callback_data="Other"
            )
        ],
    [
    InlineKeyboardButton(
                text="Back",
                callback_data="customer_back"),
      
     InlineKeyboardButton(
                text="Exit",
                callback_data="exit"
            )
    ]
    ]
    if 'search' in update.callback_query.data.strip().lower():
        bot.send_message(
            chat_id=chat_id,
            text="Please enter the name of the business you're looking for"
        )
        return SEARCH
    bot.send_message(
        chat_id=chat_id,
        text="Here's a list of categories available.\n"
        "Choose one that matches your interest.",
        reply_markup=InlineKeyboardMarkup(categories)
    )
    # print('before CHOOSE_PREF')
    return CHOOSE_PREF


def search(update, context):
    bot = context.bot
    chat_id = update.message.chat.id
    data = update.message.text.lower().strip()
    # search for business using index
    try:
        biz = client.query(
            q.get(
                q.match(
                    q.index("business_by_name"),
                    data
                )
            )
        )
        # print('BIZ ', biz)
        button = [
            [
                InlineKeyboardButton(
                    text="View All Products",
                    callback_data=biz["data"]["name"].strip().lower()
                ),
              InlineKeyboardButton(
                    text="Select for updates",
                    callback_data="pref"+','+biz["data"]["name"].strip().lower()
                )
            ],
            [
                InlineKeyboardButton(
                    text="Exit",
                    callback_data="exit"
                )
            ]
        ]
        if "latest" in biz['data'].keys():
            thumbnail = client.query(q.get(q.ref(q.collection("Product"), biz["data"]["latest"])))
            # print(thumbnail)
            bot.send_photo(
                chat_id=chat_id,
                photo=thumbnail["data"]["image"],
                caption=f"Owner - {biz['data']['name'].capitalize()}",
                reply_markup=InlineKeyboardMarkup(button)
            )
        else:
            bot.send_message(
                chat_id=chat_id,
                text=f"Owner - {biz['data']['name'].capitalize()}",
                reply_markup=InlineKeyboardMarkup(button)
                )
        return SHOW_STOCKS
    except NotFound:
        button = [
            [
                InlineKeyboardButton(
                    text="View vendors to buy from",
                    callback_data="customer"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Search for a vendor by name",
                    callback_data="customer;search"
                )
            ],
          [
                InlineKeyboardButton(
                    text="Exit",
                    callback_data="exit"
                )
            ]

        ]
        bot.send_message(
            chat_id=chat_id,
            text="Oops didn't find any vendor with that name"
            "check with your spelling to be sure its correct.",
            reply_markup=InlineKeyboardMarkup(button)
        )
        return CLASS_STATE


## BUSINESS
def business_details(update, context):
    bot = context.bot
    chat_id = update.message.chat.id
    data = update.message.text.split(',')
    if len(data) < 3 or len(data) > 3:
        bot.send_message(
            chat_id=chat_id,
            text="Invalid entry, please make sure to input the details "
            "as requested in the instructions"
        )
        return SME_DETAILS
    context.user_data["sme_dets"] = data
    # categories = [
    #         ['Clothing/Fashion', 'Hardware Accessories'],
    #         ['Food/Kitchen Ware', 'ArtnDesign'],
    #         ['Other']
    # ]
    categories = [  
        [
            InlineKeyboardButton(
                text="Food",
                callback_data="Food"
            ),
            InlineKeyboardButton(
                text="Other",
                callback_data="Other"
            )
        ]
    ]
    markup = InlineKeyboardMarkup(categories, one_time_keyboard=True)
    bot.send_message(
        chat_id=chat_id,
        text="Pick a category for your Ads",
        reply_markup=markup
    )
    return SME_CAT


def business_details_update(update, context):
    bot = context.bot
    chat_id = update.callback_query.message.chat.id
    choice = update.callback_query.data
    user_id = context.user_data['user-id']
    # biz_link = generate_link(context.user_data["sme_dets"][0])
    # create business
    new_sme = client.query(
        q.create(
            q.collection("Business"),
            {"data":{
                "name":context.user_data["sme_dets"][0].lower().strip(),
                "room":context.user_data["sme_dets"][1].strip().lower(),
                "whatsapp":context.user_data["sme_dets"][2].strip(),
                "category":choice.lower(),
                # "business_link":biz_link,
                "chat_id": chat_id
            }}
        )
    )
    context.user_data["sme_name"] = context.user_data["sme_dets"][0].strip().lower()
    context.user_data["sme_id"] = new_sme["ref"].id()
    context.user_data["sme_cat"] = choice.lower()
    # context.user_data["sme_link"] = biz_link
    button = [[
        InlineKeyboardButton(
            text="Add a product",
            callback_data=choice.lower()
        )
    ]]
    bot.send_message(
        chat_id=chat_id,
        text="Business account created successfully, "
        "let's add some products shall we!.",
        reply_markup=InlineKeyboardMarkup(button)
    )
    return ADD_PRODUCTS


def add_product(update, context):
    bot = context.bot
    chat_id = update.callback_query.message.chat.id
  
    if "back" in update.callback_query.data:
      return SELL_OR_BUY
      
    elif "exit" in update.callback_query.data:
        bot.send_message(
            chat_id=chat_id,
            text="Bye! Hope to see you soon!"
        )
        return ConversationHandler.END
      
    elif "catalogue" in update.callback_query.data:
        # print('Catalogue - We are Here!')
        context.user_data['sme_chat_id'] = chat_id
        return SME_CATALOGUE
    elif "Food" in update.callback_query.data:
        return CHOOSE_PREF
    bot.send_message(
        chat_id=chat_id,
        text="Please add title, description, and price (NUMBER only) of a product as caption to an image.\n"
        "All separated by commas (,)\ne.g.: Coca-cola, 2 left (1.5 liter), 80"
        
    )
    return ADD_PRODUCTS
  
def show_catalogue(update, context):
    # print('inside show_catalogue')
    bot = context.bot
    chat_id = context.user_data['sme_chat_id']
    # fetch products owned by business
    products = client.query(
        q.map_(
            lambda x: q.get(x),
            q.paginate(
                q.match(
                    q.index("product_by_business"),
                    context.user_data['sme_name'].lower().strip()
                )
            )
        )
    )
    if len(products['data']) == 0:
        button = [
            [
                InlineKeyboardButton(
                    text="Add products to your catalogue",
                    callback_data=chat_id
                )
            ],
          [
              InlineKeyboardButton(
                    text="Back",
                    callback_data='back'
                ),
                InlineKeyboardButton(
                    text="Exit",
                    callback_data='exit'
                )
            ]
        ]
        bot.send_message(
            chat_id=chat_id,
            text="Hi! 😃 you don't seem to have added any products yet!.",
            reply_markup=InlineKeyboardMarkup(button)
        )
        return ADD_PRODUCTS
    for product in products["data"]:
        context.user_data["sme_name"] = product['data']['sme'].strip().lower()
        button = [
            [
                InlineKeyboardButton(
                    text="Edit Info",
                    callback_data="Edit;" + product["ref"].id()
                ),
               InlineKeyboardButton(
                    text="Delete",
                    callback_data="Delete;" +product["ref"].id()
                )
            ],
            [
                InlineKeyboardButton(
                    text="Back",
                    callback_data="back"
                ),
               InlineKeyboardButton(
                    text="Exit",
                    callback_data="exit"
                )
            ]
        ]
        bot.send_photo(
            chat_id=chat_id,
            photo=product["data"]["image"],
            caption=f"{product['data']['name'].capitalize()} \nDescription: {product['data']['description']}\nPrice (som): {product['data']['price']}",
            reply_markup=InlineKeyboardMarkup(button)
        )
    return POST_VIEW_CATALOGUE
def post_show_catalogue(update, context):
    bot = context.bot
    chat_id = update.callback_query.message.chat.id
    # check for selected option
    data = update.callback_query.data
  
    if "back" in data:
        return SELL_OR_BUY
      
    elif "exit" in data:
        bot.send_message(
            chat_id=chat_id,
            text="Bye! Hope to see you soon!"
        )
        return ConversationHandler.END
      
    elif "Edit" in data:
        bot.send_message(
            chat_id=chat_id,
            text="Kindly add details for the update using the following format: "
            "{product_attribute: value}\n name/description/price \ne.g.: {price: 50} or "
            "{price: 50, description: spicy ramen}"
        )
        context.user_data['product_id'] = data.split(';')[1]
        return POST_VIEW_CATALOGUE
    # else if user chooses to remove product
    # find product and delete
    client.query(
        q.delete(
            q.ref(
                q.collection('Product'),
                data.split(';')[1]
            )
        )
    )
    button = [
        [
            InlineKeyboardButton(
                text="Go back to catalogue",
                callback_data=context.user_data['sme_name'].strip().lower()
            )
        ]
    ]
    bot.send_message(
        chat_id=chat_id,
        text="Removed product from catalogue successfully! 🗑️",
        reply_markup=InlineKeyboardMarkup(button)
    )
    return SME_CATALOGUE

def update_product_info(update, context):
    bot = context.bot
    chat_id = update.message.chat.id
    data = parse_product_info(update.message.text)
    button = [
        [
            InlineKeyboardButton(
                text="Go back to catalogue",
                callback_data=context.user_data['sme_name'].strip().lower()
            )
        ]
    ]
    if data is False:
        bot.send_message(
            chat_id=chat_id,
            text="Invalid Entry, please try again",
            reply_markup=InlineKeyboardMarkup(button)
        )
        return SME_CATALOGUE
    # if it parsed the data correctly then we can update the product info
    try:
        client.query(
            q.update(
                q.ref(
                    q.collection('Product'),
                    context.user_data['product_id']
                ),
                {'data': data}
            )
        )
        bot.send_message(
            chat_id=chat_id,
            text="Updated product details succesfully!",
            reply_markup=InlineKeyboardMarkup(button)
        )
        return SME_CATALOGUE
    except FaunaError as e:
        bot.send_message(
            chat_id=chat_id,
            text="An error occurred while trying to update the product, "
            "please try again!.",
            reply_markup=InlineKeyboardMarkup(button)
        )
        # raise(e)
        return SME_CATALOGUE


def product_info(update: Update, context: CallbackContext):
    data = update.message
    chat_id = update.message.chat_id
    bot = context.bot
    try:
        temp = update.message.caption.split(',')
      
        if len(temp) < 3 or len(temp) > 3:
            bot.send_message(chat_id=chat_id, text="Invalid entry!")
            bot.send_message(chat_id=chat_id, text="As a caption to the image, please provide Title, Description and Price (only number) seperated by comma (,)\ne.g.: Coca-cola, 1.5 liters (2 Left), 80")
            bot.send_message(chat_id=chat_id, text="Type /start, to restart bot")
            return ConversationHandler.END

    except AttributeError:
        temp = update.message.text.split(',')

    photo = bot.getFile(update.message.photo[-1].file_id)
    file_ = open('product_image.png', 'wb')
    photo.download(out=file_)
    data = update.message.caption.split(',')
    # upload image to cloudinary
    with open('product_image.png', 'rb') as file_:
        send_photo = upload(
            file_, 
            width=500, height=450, 
            crop='thumb'
        )
        # create new product
        newprod = client.query(
            q.create(
                q.collection("Product"),
                {"data": {
                        "name":data[0].strip().lower(),
                        "description":data[1].strip().lower(),
                        "price":float(data[2]),
                        "image":send_photo["secure_url"],
                        "sme":context.user_data["sme_name"].strip().lower(),
                        "sme_chat_id": update.message.chat.id,
                        "category":context.user_data["sme_cat"].lower().strip()
                    }
                }
            )
        )
        # add new product as latest
        client.query(
            q.update(
                q.ref(q.collection("Business"), context.user_data["sme_id"]),
                {"data": {
                    "latest": newprod["ref"].id()
                }}
            )
        )
        # context.user_data["product_data"] = newprod['data']
        button = [[InlineKeyboardButton(
            text='Add another product',
            callback_data=context.user_data["sme_name"].strip().lower()
        )],
                [InlineKeyboardButton(
            text='Catalogue',
            callback_data="catalogue"
        )]
                 ]
        update.message.reply_text(
            "Product added successfully",
            reply_markup=InlineKeyboardMarkup(button)
        )
      
        all_users = client.query(
          q.paginate(
            q.documents(
              q.collection("User")),
              size=100))

        for i in all_users['data']:
            iid = i.id()
            user = client.query(
              q.get(
                q.ref(
                  q.collection("User"), iid)
                    )
                  )
            user_chat_id = user['data']['chat_id']
            print(user_chat_id)
            bot.send_message(
              chat_id=user_chat_id,
              text=f"User {context.user_data['sme_name'].strip().capitalize()} added a new product - {data[0].strip().capitalize()}",
                             reply_markup=ReplyKeyboardRemove()
        )
        
        return ADD_PRODUCTS
  

def customer_pref(update, context):
    bot = context.bot
    chat_id = update.callback_query.message.chat.id
    data = update.callback_query.data
    # print(data)
    # get all businesses in category

    if "exit" in data:
        bot.send_message(
            chat_id=chat_id,
            text="Bye! Hope to see you soon!"
        )
        return ConversationHandler.END
      
    elif "back" in data:
        return SELL_OR_BUY      
    try:
        smes_ = client.query(
            q.map_(
                lambda var: q.get(var),
                q.paginate(
                    q.match(
                        q.index("business_by_category"),
                        str(data).lower().strip()
                    )
                )
            )
        )
        # print('SME_ DATA - ', smes_['data'])
        for sme in smes_["data"]:   
            # print('we are inside')
            button = [
                [
                    InlineKeyboardButton(
                        text="View All Products",
                        callback_data=sme["data"]["name"].strip().lower()
                    ),
                  InlineKeyboardButton(
                        text="Select for updates",
                        callback_data="pref"+','+sme["data"]["name"].strip().lower()
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="Back to Categories",
                        callback_data="back"
                    )
                ]
            ]
            if "latest" in sme['data'].keys():
                try:
                  # print('inside latest')
                  thumbnail = client.query(q.get(q.ref(q.collection("Product"), sme["data"]["latest"])))
                  # print('Thumbnail - ', thumbnail)
                  bot.send_photo(
                      chat_id=chat_id,
                      photo=thumbnail["data"]["image"],
                      caption=f"Owner - {sme['data']['name'].capitalize()}",
                      reply_markup=InlineKeyboardMarkup(button)
                  )
                except:
                    pass
            # else:
            #     bot.send_message(
            #         chat_id=chat_id,
            #         text=f"{sme['data']['name'].capitalize()}",
            #         reply_markup=InlineKeyboardMarkup(button)
                # )
        return SHOW_STOCKS
    except Exception as e:
        print(e)
        button = [[
            InlineKeyboardButton(
                text="Select another Category?",
                callback_data="customer"
            )
        ]]
        bot.send_message(
            chat_id=chat_id,
            text="Nothing here yet",
            reply_markup=InlineKeyboardMarkup(button)
        )
        return CLASS_STATE


def show_products(update, context):
    bot = context.bot
    chat_id = update.callback_query.message.chat.id
    data = update.callback_query.data.strip().lower()
    # print(f'show_products |{str(update.callback_query.data).strip().lower()}')
    if 'exit' in data:
      return SELL_OR_BUY
    elif 'back' in data:
      return CLASS_STATE
    elif "pref" in  data:
        data = data.split(',')[1]
        # print(data)
        user = client.query(
            q.get(
                q.match(
                    q.index('user_by_name'), 
                    context.user_data['user-data']['name'].strip().lower()
                )
            )
        )
        # update preference
        client.query(
            q.update(
                q.ref(
                    q.collection('User'), user['ref'].id()
                ),
                {'data': {'preference': user['data']['preference']+data+','}}
            )
        )
        button = [
            [
                InlineKeyboardButton(
                    text="View more businesses category",
                    callback_data='customer'
                )
            ]
        ]
        bot.send_message(
            chat_id=chat_id,
            text="Updated preference successfully!!"
        )
        return CLASS_STATE
    products = client.query(
        q.map_(
            lambda x: q.get(x),
            q.paginate(
                q.match(
                    q.index("product_by_business"),
                    update.callback_query.data.strip().lower()
                )
            )
        )
    )
    # print(products)
    if len(products['data']) == 0:
        button = [
            [
                InlineKeyboardButton(
                    text="Back to Categories",
                    callback_data="customer"
                )
            ]
        ]
        bot.send_message(
            chat_id=chat_id,
            text="Nothing here yet, users haven't added any products!, check back later",
            reply_markup=InlineKeyboardMarkup(button)
        )
        return CLASS_STATE
    for product in products["data"]:
        context.user_data["sme_id"] = product['data']['sme'].strip().lower()
        button = [
            [
                InlineKeyboardButton(
                    text="Send Order",
                    callback_data="order;" + product["ref"].id()
                ),
              InlineKeyboardButton(
                    text="Vendor's Contacts",
                    callback_data="contact;" + product["data"]["sme"].strip().lower()
                )
            ],
            [
                InlineKeyboardButton(
                    text="Back",
                    callback_data="back"
                ),
                InlineKeyboardButton(
                    text="Exit",
                    callback_data="exit"
                )
            ]
        ]
        bot.send_photo(
            chat_id=chat_id,
            photo=product["data"]["image"],
            caption=f"{product['data']['name']} \nDescription: {product['data']['description']}\nPrice (som): {product['data']['price']}",
            reply_markup=InlineKeyboardMarkup(button)
        )
    return POST_VIEW_PRODUCTS

def post_view_products(update, context):
    bot = context.bot
    chat_id = update.callback_query.message.chat.id
    data = update.callback_query.data

    if "back" in data:
        return CLASS_STATE
      
    elif "exit" in data:
        bot.send_message(
            chat_id=chat_id,
            text="Bye! Hope to see you soon!"
        )
        return ConversationHandler.END
      
    elif "order" in data:
        product = client.query(
        q.get(
            q.ref(
                    q.collection("Product"),
                    data.split(';')[1]
                )
            )
        )["data"]
        bot.send_message(
            chat_id=product['sme_chat_id'],
            text="Hey you have a new order"
        )
        bot.send_photo(
            chat_id=product['sme_chat_id'],
            caption=f"Name: {product['name']}\n\nDescription: {product['description']}\n\nPrice: {product['price']}"
            f"\n\n Customer's Name: {context.user_data['user-name']}",
            photo=product['image']
        )  
        bot.send_contact(
            chat_id=product['sme_chat_id'],
            phone_number=context.user_data['user-data']['whatsapp'],
            first_name=context.user_data['user-data']['name']
        )
        print(f"{context.user_data['user-data']['name'].upper()}\tsend order to \t{product['sme'].upper()}")
        bot.send_message(
            chat_id=chat_id,
            text="Placed order successfully"
        )
        bot.send_message(
            chat_id=chat_id,
            text="/start - restart the bot\n/cancel - stop the bot"
        )
    elif 'contact' in data:
        button = [
          [
        InlineKeyboardButton(
            text="Back",
            callback_data="back"
        ),
        InlineKeyboardButton(
            text="Exit",
            callback_data="exit"
        )
          ]
        ]
        sme_ = client.query(
            q.get( 
                q.match(
                    q.index("business_by_name"), 
                    data.split(';')[1]
                )
            )
        )['data']
        bot.send_message(
            chat_id=chat_id,
            text=f"Owner: {sme_['name'].capitalize()}\nWhatsApp: {sme_['whatsapp']}\nRoom: {sme_['room'].upper()}",
          reply_markup=InlineKeyboardMarkup(button)
        )
        print(f"{context.user_data['user-data']['name'].upper()}\tviewed contacts of\t{sme_['name'].upper()}")
        return CLASS_STATE

# Control
def cancel(update: Update, context: CallbackContext) -> int: 
    update.message.reply_text(
        'Bye, hope to see you soon!',
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END

def help(update: Update, context: CallbackContext) -> str: 
    update.message.reply_text(
        "/start - run the bot\n/cancel - stop the bot\n/help - help message and developer contacts\nSometimes you may need to wait or click a button two times 😅\nIn any case, please feel free to contact Shukur\nWhatsApp - +79014077195\nTelegram - +992934000005\nTutorial video on how to make a post - https://drive.google.com/file/d/1JW1hDmeeOH5UM-F3HhWdBUDQheGe4vEB/view?usp=sharing",
        reply_markup=ReplyKeyboardRemove()
    )
    update.message.reply_text(
        "/start Restart the bot",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def search_(update, context):
    bot = context.bot
    chat_id = update.message.chat.id
    bot.send_message(
        chat_id=chat_id,
        text="Please enter the name of the business you're looking for"
    )
    return SEARCH


def parse_product_info(data:str):
    dic_ = {}
    parsed_ = data.replace('}','')
    parsed_ = parsed_.replace('{','')
    parsed_ = parsed_.split(',')
    print(parsed_)
    for item in parsed_:
        if len(item.split(':')) == 2:
            data_ = item.split(':')
            print(data_)
            dic_[data_[0]] = data_[1]
        else:
            return False
    return dic_