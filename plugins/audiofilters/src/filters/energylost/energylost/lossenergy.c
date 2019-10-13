#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <math.h>
#include <limits.h>
#include <assert.h>

#include <fftw3.h>

//#include <sndfile.h>

#include "window.h"
#include "common.h"
#include "spectrum.h"

#define TICK_LEN			6

#define	SPEC_FLOOR_DB		-180.0


typedef struct
{	const char *sndfilepath, *filename ;
	int width, height ;
	bool border, log_freq, gray_scale ;
	double min_freq, max_freq, fft_freq ;
	enum WINDOW_FUNCTION window_function ;
	double spec_floor_db ;
} RENDER ;

typedef struct
{	int left, top, width, height ;
} RECT ;

static void
read_mono_audio (SNDFILE * file, sf_count_t filelen, double * data, int datalen, int indx, int total)
{
	sf_count_t start ;

	memset (data, 0, datalen * sizeof (data [0])) ;

	start = (indx * filelen) / total - datalen / 2 ;

	if (start >= 0)
		sf_seek (file, start, SEEK_SET) ;
	else
	{	start = -start ;
		sf_seek (file, 0, SEEK_SET) ;
		data += start ;
		datalen -= start ;
		} ;

	sfx_mix_mono_read_double (file, data, datalen) ;

	return ;
} /* read_mono_audio */


/* The greatest number of linear ticks seems to occurs from 0-14000 (15 ticks).
** The greatest number of log ticks occurs 10-99999 or 11-100000 (35 ticks).
** Search for "worst case" for the commentary below that says why it is 35.
*/
typedef struct
{	double value [40] ;  /* 35 or more */
	double distance [40] ;
	/* The digit that changes from label to label.
	** This ensures that a range from 999 to 1001 prints 999.5 and 1000.5
	** instead of 999 1000 1000 1000 1001.
	*/
	int decimal_places_to_print ;
} TICKS ;

/* Decide where to put ticks and numbers on an axis.
**
** Graph-labelling convention is that the least significant digit that changes
** from one label to the next should change by 1, 2 or 5, so we step by the
** largest suitable value of 10^n * {1, 2 or 5} that gives us the required
** number of divisions / numeric labels.
*/

/* The old code used to make 6 to 14 divisions and number every other tick.
** What we now mean by "division" is one of teh gaps between numbered segments
** so we ask for a minimum of 3 to give the same effect as the old minimum of
** 6 half-divisions.
** This results in the same axis labelling for all maximum values
** from 0 to 12000 in steps of 1000 and gives sensible results from 13000 on,
** to a maximum of 7 divisions and 8 labels from 0 to 14000.
**/
#define TARGET_DIVISIONS 3

/* Value to store in the ticks.value[k] field to mean
** "Put a tick here, but don't print a number."
** NaN (0.0/0.0) is untestable without isnan() so use a random value.
*/
#define NO_NUMBER (M_PI)		/* They're unlikely to hit that! */

/* Is this entry in "ticks" one of the numberless ticks? */
#define JUST_A_TICK(ticks, k)	(ticks.value [k] == NO_NUMBER)

/* A tolerance to use in floating point < > <= >= comparisons so that
** imprecision doesn't prevent us from printing an initial or final label
** if it should fall exactly on min or max but doesn't due to FP problems.
** For example, for 0-24000, the calculations might give 23999.9999999999.
*/
#define DELTA (1e-10)

static int	/* Forward declaration */
calculate_log_ticks (double min, double max, double distance, TICKS * ticks) ;

/* log_scale is pseudo-boolean:
** 0 means use a linear scale,
** 1 means use a log scale and
** 2 is an internal value used when calling back from calculate_log_ticks() to
**   label the range with linear numbering but logarithmic spacing.
*/

static int
calculate_ticks (double min, double max, double distance, int log_scale, TICKS * ticks)
{
	double step ;	/* Put numbered ticks at multiples of this */
	double range = max - min ;
	int k ;
	double value ;	/* Temporary */

	if (log_scale == 1)
		return calculate_log_ticks (min, max, distance, ticks) ;

	/* Linear version */

	/* Choose a step between successive axis labels so that one digit
	** changes by 1, 2 or 5 amd that gives us at least the number of
	** divisions (and numberic labels) that we would like to have.
	**
	** We do this by starting "step" at the lowest power of ten <= max,
	** which can give us at most 9 divisions (e.g. from 0 to 9999, step 1000)
	** Then try 5*this, 2*this and 1*this.
	*/
	step = pow (10.0, floor (log10 (max))) ;
	do
	{	if (range / (step * 5) >= TARGET_DIVISIONS)
		{	step *= 5 ;
			break ;
			} ;
		if (range / (step * 2) >= TARGET_DIVISIONS)
		{	step *= 2 ;
			break ;
			} ;
		if (range / step >= TARGET_DIVISIONS)
			break ;
		step /= 10 ;
	} while (1) ;	/* This is an odd loop! */

	/* Ensure that the least significant digit that changes gets printed, */
	ticks->decimal_places_to_print = lrint (-floor (log10 (step))) ;
	if (ticks->decimal_places_to_print < 0)
		ticks->decimal_places_to_print = 0 ;

	/* Now go from the first multiple of step that's >= min to
	 * the last one that's <= max. */
	k = 0 ;
	value = ceil (min / step) * step ;

#define add_tick(val, just_a_tick) do \
	{	if (val >= min - DELTA && val < max + DELTA) \
		{	ticks->value [k] = just_a_tick ? NO_NUMBER : val ; \
			ticks->distance [k] = distance * \
				(log_scale == 2 \
					? /*log*/ (log (val) - log (min)) / (log (max) - log (min)) \
					: /*lin*/ (val - min) / range) ; \
			k++ ; \
			} ; \
		} while (0)

	/* Add the half-way tick before the first number if it's in range */
	add_tick (value - step / 2, true) ;

	while (value <= max + DELTA)
	{ 	/* Add a tick next to each printed number */
		add_tick (value, false) ;

		/* and at the half-way tick after the number if it's in range */
		add_tick (value + step / 2, true) ;

		value += step ;
		} ;

	return k ;
} /* calculate_ticks */

/* Number/tick placer for logarithmic scales.
**
** Some say we should number 1, 10, 100, 1000, 1000 and place ticks at
** 2,3,4,5,6,7,8,9, 20,30,40,50,60,70,80,90, 200,300,400,500,600,700,800,900
** Others suggest numbering 1,2,5, 10,20,50, 100,200,500.
**
** Ticking 1-9 is visually distinctive and emphasizes that we are using
** a log scale, as well as mimicking log graph paper.
** Numbering the powers of ten and, if that doesn't give enough labels,
** numbering also the 2 and 5 multiples might work.
**
** Apart from our [number] and tick styles:
** [1] 2 5 [10] 20 50 [100]  and
** [1] [2] 3 4 [5] 6 7 8 9 [10]
** the following are also seen in use:
** [1] [2] 3 4 [5] 6 7 [8] 9 [10]  and
** [1] [2] [3] [4] [5] [6] 7 [8] 9 [10]
** in https://www.lhup.edu/~dsimanek/scenario/errorman/graphs2.htm
**
** This works fine for wide ranges, not so well for narrow ranges like
** 5000-6000, so for ranges less than a decade we apply the above
** linear numbering style 0.2 0.4 0.6 0.8 or whatever, but calulating
** the positions of the legends logarithmically.
**
** Alternatives could be:
** - by powers or two from some starting frequency
**   defaulting to the Nyquist frequency (22050, 11025, 5512.5 ...) or from some
**   musical pitch (220, 440, 880, 1760)
** - with a musical note scale  C0 ' D0 ' E0 F0 ' G0 ' A0 ' B0 C1
** - with manuscript staff lines, piano note or guitar string overlay.
*/

/* Helper functions: add ticks and labels at start_value and all powers of ten
** times it that are in the min-max range.
** This is used to plonk ticks at 1, 10, 100, 1000 then at 2, 20, 200, 2000
** then at 5, 50, 500, 5000 and so on.
*/
static int
add_log_ticks (double min, double max, double distance, TICKS * ticks,
				int k, double start_value, bool include_number)
{	double value ;

	for (value = start_value ; value <= max + DELTA ; value *= 10.0)
	{	if (value < min - DELTA) continue ;
		ticks->value [k] = include_number ? value : NO_NUMBER ;
		ticks->distance [k] = distance * (log (value) - log (min)) / (log (max) - log (min)) ;
		k++ ;
		} ;
	return k ;
} /* add_log_ticks */

static int
calculate_log_ticks (double min, double max, double distance, TICKS * ticks)
{	int k = 0 ;	/* Number of ticks we have placed in "ticks" array */
	double underpinning ; 	/* Largest power of ten that is <= min */

	/* If the interval is less than a decade, just apply the same
	** numbering-choosing scheme as used with linear axis, with the
	** ticks positioned logarithmically.
	*/
	if (max / min < 10.0)
		return calculate_ticks (min, max, distance, 2, ticks) ;

	/* If the range is greater than 1 to 1000000, it will generate more than
	** 19 ticks.  Better to fail explicitly than to overflow.
	*/
	if (max / min > 1000000)
	{	printf ("Error: Frequency range is too great for logarithmic scale.\n") ;
		exit (1) ;
		} ;

	/* First hack: label the powers of ten. */

 	/* Find largest power of ten that is <= minimum value */
	underpinning = pow (10.0, floor (log10 (min))) ;

	/* Go powering up by 10 from there, numbering as we go. */
	k = add_log_ticks (min, max, distance, ticks, k, underpinning, true) ;

	/* Do we have enough numbers? If so, add numberless ticks at 2 and 5 */
	if (k >= TARGET_DIVISIONS + 1) /* Number of labels is n.of divisions + 1 */
	{
		k = add_log_ticks (min, max, distance, ticks, k, underpinning * 2.0, false) ;
		k = add_log_ticks (min, max, distance, ticks, k, underpinning * 5.0, false) ;
		}
	else
	{	int i ;
		/* Not enough numbers: add numbered ticks at 2 and 5 and
		 * unnumbered ticks at all the rest */
		for (i = 2 ; i <= 9 ; i++)
			k = add_log_ticks (min, max, distance, ticks, k,
								underpinning * (1.0 * i), i == 2 || i == 5) ;
		} ;

	/* Greatest possible number of ticks calculation:
	** The worst case is when the else clause adds 8 ticks with the maximal
	** number of divisions, which is when k == TARGET_DIVISIONS, 3,
	** for example 100, 1000, 10000.
	** The else clause adds another 8 ticks inside each division as well as
	** up to 8 ticks after the last number (from 20000 to 90000)
	** and 8 before to the first (from 20 to 90 in the example).
	** Maximum possible ticks is 3+8+8+8+8=35
	*/

	return k ;
} /* calculate_log_ticks */



/* Pick the best FFT length good for FFTW?
**
** We use fftw_plan_r2r_1d() for which the documantation
** http://fftw.org/fftw3_doc/Real_002dto_002dReal-Transforms.html says:
**
** "FFTW is generally best at handling sizes of the form
** 2^a 3^b 5^c 7^d 11^e 13^f
** where e+f is either 0 or 1, and the other exponents are arbitrary."
*/

/* Helper function: does N have only 2, 3, 5 and 7 as its factors? */
static bool
is_2357 (int n)
{
	/* Just eliminate all factors os 2, 3, 5 and 7 and see if 1 remains */
	while (n % 2 == 0) n /= 2 ;
	while (n % 3 == 0) n /= 3 ;
	while (n % 5 == 0) n /= 5 ;
	while (n % 7 == 0) n /= 7 ;
	return (n == 1) ;
}

/* Helper function: is N a "fast" value for the FFT size? */
static bool
is_good_speclen (int n)
{
	/* It wants n, 11*n, 13*n but not (11*13*n)
	** where n only has as factors 2, 3, 5 and 7
	*/
	if (n % (11 * 13) == 0) return 0 ; /* No good */

	return is_2357 (n)	|| ((n % 11 == 0) && is_2357 (n / 11))
						|| ((n % 13 == 0) && is_2357 (n / 13)) ;
}

static void
render_to_surface (const RENDER * render, SNDFILE *infile, int samplerate, sf_count_t filelen)
{


	spectrum *spec ;
	int width,height ,w, speclen ;
	width = render->width;
	height = render->height ;


	/*
	** Choose a speclen value, the spectrum length.
	** The FFT window size is twice this.
	*/
	if (render->fft_freq != 0.0)
		/* Choose an FFT window size of 1/fft_freq seconds of audio */
		speclen = (samplerate / render->fft_freq + 1) / 2 ;
	else
		/* Long enough to represent frequencies down to 20Hz. */
		speclen = height * (samplerate / 20 / height + 1) ;

	/* Find the nearest fast value for the FFT size. */
	{	int d ;	/* difference */

		for (d = 0 ; /* Will terminate */ ; d++)
		{	/* Logarithmically, the integer above is closer than
			** the integer below, so prefer it to the one below.
			*/
			if (is_good_speclen (speclen + d))
			{	speclen += d ;
				break ;
				}
			/* FFT length must also be >= the output height,
			** otherwise repeated pixel rows occur in the output.
			*/
			if (speclen - d >= height && is_good_speclen (speclen - d))
			{	speclen -= d ;
				break ;
				}
			}
		}



	//hhl
	float ** spec_x = NULL ; // Indexed by [w][h]
	spec_x = calloc (width, sizeof (float *)) ;
	if (spec_x == NULL)
	{	printf ("%s : Not enough memory.\n", __func__) ;
		exit (1) ;
		} ;
	for (w = 0 ; w < width ; w++)
	{	if ((spec_x [w] = calloc (speclen, sizeof (float))) == NULL)
		{	printf ("%s : Not enough memory.\n", __func__) ;
			exit (1) ;
			} ;
		} ;

	spec = create_spectrum (speclen, render->window_function) ;

	if (spec == NULL)
	{	printf ("%s : line %d : create plan failed.\n", __FILE__, __LINE__) ;
		exit (1) ;
		} ;

	for (w = 0 ; w < width ; w++)
	{	double single_max ;

		read_mono_audio (infile, filelen, spec->time_domain, 2 * speclen, w, width) ;

		single_max = calc_magnitude_spectrum (spec) ;

		//hhl
		for (int spec_i = 0 ; spec_i < speclen ; spec_i++)
			{
				spec_x[w][spec_i]=spec->mag_spec[spec_i];
				//printf("%.2f  ",spec_x[w][i]);
			};
		//printf("\n %d \n",i);

	} ;


	//按照频率进行检查
	float * spec_sum = NULL ; 
	spec_sum = calloc (speclen, sizeof (float *)) ;
	for (int spec_i = 0 ; spec_i < speclen ; spec_i++)
		for (w = 0 ; w < width ; w++)
		{
			spec_sum[spec_i]+=spec_x[w][spec_i];
		}
    

	int count1=0,count2=0;;
	for (int spec_i = 450 ; spec_i < speclen ; spec_i++)
	{
		if (spec_sum[spec_i]<0.5) count1++;
		if (spec_sum[spec_i]<1) count2++;
		//for debug
		//printf("%.3f\t",spec_sum[spec_i]);
	}
	if (count1>50&&count2>100) 
		printf("invalid\t%d|%d\n",count1,count2) ;
	else
		printf("ok\n") ;
	

	destroy_spectrum (spec) ;

	return ;
} /* render_to_surface */

static void
render_sndfile (RENDER * render)
{
	SNDFILE *infile ;
	SF_INFO info ;

	memset (&info, 0, sizeof (info)) ;

	infile = sf_open (render->sndfilepath, SFM_READ, &info) ;
	if (infile == NULL)
	{	printf ("Error : failed to open file '%s' : \n%s\n", render->sndfilepath, sf_strerror (NULL)) ;
		exit (1) ;
		} ;

	if (render->max_freq == 0.0)
		render->max_freq = (double) info.samplerate / 2 ;
	if (render->min_freq == 0.0 && render->log_freq)
		render->min_freq = 20.0 ;

	/* Do this sanity check here, as soon as max_freq has its default value */
	if (render->min_freq >= render->max_freq)
	{	printf ("Error : --min-freq (%g) must be less than max_freq (%g)\n",
			render->min_freq, render->max_freq) ;
		exit (1) ;
		} ;
	render_to_surface (render, infile, info.samplerate, info.frames);

	sf_close (infile) ;

	return ;
} /* render_sndfile */


int
main (int argc, char * argv [])
{	

	RENDER render =
	{	NULL, NULL,
		0, 0,				/* width, height */
		true, false, false, /* border, log_freq, gray_scale */
		0.0, 0.0, 0.0,		/* {min,max,fft}_freq */
		KAISER,
		SPEC_FLOOR_DB
		} ;
	if (argc < 2)
		{
			printf("Usage :%s <sound file>\n",argv[0] );
			exit (0) ;
		}

	render.sndfilepath = argv[1] ;
	render.width = 1000 ; //改为2000更好（少检测1个错误），但1000更快
	render.height = 100 ;

	render.filename = strrchr (render.sndfilepath, '/') ;
	render.filename = (render.filename != NULL) ? render.filename + 1 : render.sndfilepath ;

	render_sndfile (&render) ;

	return 0 ;
} /* main */
