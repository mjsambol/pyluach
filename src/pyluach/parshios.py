"""The parshios module has functions to find the weekly parasha.

Examples
--------
>>> from pyluach import dates, parshios
>>> date = dates.HebrewDate(5781, 10, 5)
>>> parshios.getparsha_string(date)
'Vayigash'
>>> parshios.getparsha_string(date, hebrew=True)
'ויגש'
>>> parshios.getparsha_string(dates.GregorianDate(2021, 3, 7), hebrew=True)
'ויקהל, פקודי'

Note
----
The algorithm is based on Dr. Irv Bromberg's, University of Toronto at
http://individual.utoronto.ca/kalendis/hebrew/parshah.htm

Several options are available for style of transliteration; the default is American Ashkenazik.


Attributes
----------
PARSHIOS_ASHKENAZ : list of str
    A list of the parshios transliterated into English, with Ashkenasic transliteration.
PARSHIOS_ISRAELI_1 : list of str
    A list of the parshios transliterated into English, with mixed Israeli transliteration.
PARSHIOS_ISRAELI_2 : list of str
    A list of the parshios transliterated into English, with modern Israeli transliteration.
PARSHIOS_HEBREW : list of str
    A list of the parshios in Hebrew.
"""

from collections import deque, OrderedDict
from functools import lru_cache

from pyluach.dates import HebrewDate
from pyluach.utils import _is_leap, Transliteration


PARSHIOS_ASHKENAZ = [
    'Bereishis', 'Noach', 'Lech Lecha', 'Vayeira', 'Chayei Sarah', 'Toldos',
    'Vayeitzei', 'Vayishlach', 'Vayeishev', 'Mikeitz', 'Vayigash', 'Vayechi',
    'Shemos', "Va'eira", 'Bo', 'Beshalach', 'Yisro', 'Mishpatim', 'Terumah',
    'Tetzaveh', 'Ki Sisa', 'Vayakhel', 'Pekudei', 'Vayikra', 'Tzav', 'Shemini',
    'Tazria', 'Metzora', 'Acharei Mos', 'Kedoshim', 'Emor', 'Behar',
    'Bechukosai', 'Bamidbar', 'Nasso', "Beha'aloscha", 'Shelach', 'Korach',
    'Chukas', 'Balak', 'Pinchas', 'Mattos', 'Masei', 'Devarim', "Va'eschanan",
    'Eikev', "Re'eh", 'Shoftim', 'Ki Seitzei', 'Ki Savo', 'Nitzavim',
    'Vayeilech', 'Haazinu', 'Vezos Haberachah'
]

PARSHIOT_ISRAELI_MIXED = [
    'Bereishit', 'Noach', 'Lech Lecha', 'Vayeira', 'Chayei Sarah', 'Toldot',
    'Vayeitzei', 'Vayishlach', 'Vayeishev', 'Mikeitz', 'Vayigash', 'Vayechi',
    'Shemot', "Va'eira", 'Bo', 'Beshalach', 'Yitro', 'Mishpatim', 'Terumah',
    'Tetzaveh', 'Ki Tisa', 'Vayakhel', 'Pekudei', 'Vayikra', 'Tzav', 'Shemini',
    'Tazria', 'Metzora', 'Acharei Mot', 'Kedoshim', 'Emor', 'Behar',
    'Bechukotai', 'Bamidbar', 'Nasso', "Beha'alotcha", 'Shelach', 'Korach',
    'Chukat', 'Balak', 'Pinchas', 'Mattot', 'Masei', 'Devarim', "Va'etchanan",
    'Eikev', "Re'eh", 'Shoftim', 'Ki Teitzei', 'Ki Tavo', 'Nitzavim',
    'Vayeilech', 'Haazinu', 'Vezot Haberachah'
]

PARSHIOT_ISRAELI_MODERN = [
    'Bereshit', 'Noach', 'Lech Lecha', 'Vayera', 'Chayei Sarah', 'Toldot',
    'Vayetze', 'Vayishlach', 'Vayeshev', 'Miketz', 'Vayigash', 'Vayechi',
    'Shmot', "Va'era", 'Bo', 'Beshalach', 'Yitro', 'Mishpatim', 'Trumah',
    'Tetzaveh', 'Ki Tisa', 'Vayakhel', 'Pekudei', 'Vayikra', 'Tzav', 'Shmini',
    'Tazria', 'Metzora', 'Achrei Mot', "K'doshim", 'Emor', 'Behar',
    'Bechukotai', 'Bamidbar', 'Nasso', "Beha'alotcha", 'Shlach', 'Korach',
    'Chukat', 'Balak', 'Pinchas', 'Mattot', 'Masei', 'Dvarim', "Va'etchanan",
    'Ekev', "Re'eh", 'Shoftim', 'Ki Tetze', 'Ki Tavo', 'Nitzavim',
    'Vayelech', 'Haazinu', 'Vezot Habracha'
]

PARSHIOS_HEBREW = [
    'בראשית', 'נח', 'לך לך', 'וירא', 'חיי שרה', 'תולדות', 'ויצא', 'וישלח',
    'וישב', 'מקץ', 'ויגש', 'ויחי', 'שמות', 'וארא', 'בא', 'בשלח', 'יתרו',
    'משפטים', 'תרומה', 'תצוה', 'כי תשא', 'ויקהל', 'פקודי', 'ויקרא', 'צו',
    'שמיני', 'תזריע', 'מצורע', 'אחרי מות', 'קדושים', 'אמור', 'בהר', 'בחוקותי',
    'במדבר', 'נשא', 'בהעלותך', 'שלח', 'קרח', 'חקת', 'בלק', 'פינחס', 'מטות',
    'מסעי', 'דברים', 'ואתחנן', 'עקב', 'ראה', 'שופטים', 'כי תצא', 'כי תבא',
    'נצבים', 'וילך', 'האזינו', 'וזאת הברכה'
]

PARSHA_NAMES_IN_EN = {Transliteration.ASHKENAZ: PARSHIOS_ASHKENAZ, 
                      Transliteration.MIXED_ISRAELI: PARSHIOT_ISRAELI_MIXED, 
                      Transliteration.MODERN_ISRAELI: PARSHIOT_ISRAELI_MODERN}

def _parshaless(date, israel=False):
    if israel and date.tuple()[1:] in [(7, 23), (1, 22), (3, 7)]:
        return False
    if date.month == 7 and date.day in ([1, 2, 10] + list(range(15, 24))):
        return True
    if date.month == 1 and date.day in range(15, 23):
        return True
    if date.month == 3 and date.day in [6, 7]:
        return True
    return False


@lru_cache(maxsize=50)
def _gentable(year, israel=False):
    """Return OrderedDict mapping date of Shabbos to list of parsha numbers.

    The numbers start with Beraishis as 0. Double parshios are represented
    as a list of the two numbers. If there is no Parsha the value is None.
    """
    parshalist = deque([51, 52] + list(range(52)))
    table = OrderedDict()
    leap = _is_leap(year)
    pesachday = HebrewDate(year, 1, 15).weekday()
    rosh_hashana = HebrewDate(year, 7, 1)
    shabbos = rosh_hashana.shabbos()
    if rosh_hashana.weekday() > 4:
        parshalist.popleft()

    while shabbos.year == year:
        if _parshaless(shabbos, israel):
            table[shabbos] = None
        else:
            parsha = parshalist.popleft()
            table[shabbos] = [parsha]
            if (
                (parsha == 21 and (HebrewDate(year, 1, 14) - shabbos) // 7 < 3)
                or (parsha in [26, 28] and not leap)
                or (
                    parsha == 31 and not leap
                    and (not israel or pesachday != 7)
                )
                or (parsha == 38 and not israel and pesachday == 5)
                or (parsha == 41 and (HebrewDate(year, 5, 9)-shabbos) // 7 < 2)
                or (parsha == 50 and HebrewDate(year+1, 7, 1).weekday() > 4)
            ):
                #  If any of that then it's a double parsha.
                table[shabbos].append(parshalist.popleft())
        shabbos += 7
    return table


def getparsha(date, israel=False):
    """Return the parsha for a given date.

    Returns the parsha for the Shabbos on or following the given
    date.

    Parameters
    ----------
    date : ~pyluach.dates.BaseDate
      Any subclass of ``BaseDate``. This date does not have to be a Shabbos.

    israel : bool, optional
      ``True`` if you want the parsha according to the Israel schedule
      (with only one day of Yom Tov). Defaults to ``False``.

    Returns
    -------
    list of int or None
      A list of the numbers of the parshios for the Shabbos of the given date,
      beginning with 0 for Beraishis, or ``None`` if the Shabbos doesn't
      have a parsha (i.e. it's on Yom Tov).
    """
    shabbos = date.to_heb().shabbos()
    table = _gentable(shabbos.year, israel)
    return table[shabbos]


def getparsha_string(date, israel=False, hebrew=False, transliteration=Transliteration.ASHKENAZ):
    """Return the parsha as a string for the given date.

    This function wraps ``getparsha`` returning the parsha name.

    Parameters
    ----------
    date : ~pyluach.dates.BaseDate
      Any subclass of ``BaseDate``. The date does not have to be a Shabbos.

    israel : bool, optional
      ``True`` if you want the parsha according to the Israel schedule
      (with only one day of Yom Tov). Default is ``False``.

    hebrew : bool, optional
      ``True`` if you want the name of the parsha in Hebrew.
      Default is ``False``.

    transliteration : enum, optional
      Determines which style of transliteration English spellings should follow
      Default is ``utils.Transliteration.ASHKENAZ`` for backward compatibility with the original pyluach implementation

    Returns
    -------
    str or None
      The name of the parsha separated by a comma and space if it is a
      double parsha or ``None`` if there is no parsha that Shabbos
      (ie. it's yom tov).
    """
    parsha = getparsha(date, israel)
    if parsha is None:
        return None
    if not hebrew:
        name = [PARSHA_NAMES_IN_EN[transliteration][n] for n in parsha]
    else:
        name = [PARSHIOS_HEBREW[n] for n in parsha]
    return ', '.join(name)


def iterparshios(year, israel=False):
    """Generate all the parshios in the year.

    Parameters
    ----------
    year : int
      The Hebrew year to get the parshios for.

    israel : bool, optional
      ``True`` if you want the parsha according to the Israel schedule
      (with only one day of Yom Tov). Defaults to ``False``

    Yields
    ------
    :obj:`list` of :obj:`int` or :obj:`None`
      A list of the numbers of the parshios for the next Shabbos in the
      given year. Yields ``None`` for a Shabbos that doesn't have its
      own parsha (i.e. it occurs on a yom tov).
    """
    table = _gentable(year, israel)
    for shabbos in table.values():
        yield shabbos


def parshatable(year, israel=False):
    """Return a table of all the Shabbosos in the year

    Parameters
    ----------
    year : int
      The Hebrew year to get the parshios for.

    israel : bool, optional
      ``True`` if you want the parshios according to the Israel
      schedule (with only one day of Yom Tov). Defaults to ``False``.

    Returns
    -------
    ~collections.OrderedDict
      An ordered dictionary with the ``HebrewDate`` of each Shabbos
      as the key mapped to the parsha as a list of ints, or ``None`` for a
      Shabbos with no parsha.
    """
    return _gentable(year, israel)
