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

#define FRAME_DETECT 1000 //检测1000帧，1帧8个采样点，因为16K的采样率，所以是0.5秒


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

typedef struct
{	double value [40] ;  /* 35 or more */
	double distance [40] ;
	int decimal_places_to_print ;
} TICKS ;


#define TARGET_DIVISIONS 3

#define NO_NUMBER (M_PI)		/* They're unlikely to hit that! */

/* Is this entry in "ticks" one of the numberless ticks? */
#define JUST_A_TICK(ticks, k)	(ticks.value [k] == NO_NUMBER)

#define DELTA (1e-10)

static int	/* Forward declaration */
calculate_log_ticks (double min, double max, double distance, TICKS * ticks) ;

static int
calculate_ticks (double min, double max, double distance, int log_scale, TICKS * ticks)
{
	double step ;	/* Put numbered ticks at multiples of this */
	double range = max - min ;
	int k ;
	double value ;	/* Temporary */

	if (log_scale == 1)
		return calculate_log_ticks (min, max, distance, ticks) ;

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

	return k ;
} /* calculate_log_ticks */



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

int
render_to_surface (const RENDER * render, SNDFILE *infile, int samplerate, sf_count_t filelen)
{


	spectrum *spec ;
	int width,height ,w, speclen ;
	width = ceil(filelen/8); //8个采样点为一帧
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
	spec_x = calloc (FRAME_DETECT, sizeof (float *)) ;
	if (spec_x == NULL)
	{	printf ("%s : Not enough memory.\n", __func__) ;
		exit (1) ;
		} ;
	for (w = 0 ; w < FRAME_DETECT ; w++)
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

	for (w = 0 ; w < FRAME_DETECT ; w++)
	{	double single_max ;

		read_mono_audio (infile, filelen, spec->time_domain, 2 * speclen, w, width) ;

		single_max = calc_magnitude_spectrum (spec) ;


		//hhl
		for (int spec_i = 0 ; spec_i < speclen ; spec_i++)
			{
				spec_x[w][spec_i]=spec->mag_spec[spec_i];
				//printf("%.2f ",spec_x[w][spec_i]);
			};
		//printf("\n");

	} ;


	//hhl
	float * spec_sum = NULL ; 
	spec_sum = calloc (speclen, sizeof (float *)) ;
	for (int spec_i = 0 ; spec_i < speclen ; spec_i++)
		for (w = 0 ; w < FRAME_DETECT ; w++)
		{
			spec_sum[spec_i]+=spec_x[w][spec_i];
		}
	
	
	float * std = NULL ; 
	std = calloc (speclen, sizeof (float *)) ;
	for (int spec_i = 0 ; spec_i < speclen ; spec_i++)
	{
		for (w = 0 ; w < FRAME_DETECT ; w++)
		{
			std[spec_i]+=(spec_x[w][spec_i]-spec_sum[spec_i]/FRAME_DETECT)*(spec_x[w][spec_i]-spec_sum[spec_i]/FRAME_DETECT);
		}
	}

	
    //printf("_____________std______________\n");
    int count1=0; //一条线那种，排除低频部分。200Hz之于8000HZ，50分频之于2000分频
	for (int spec_i = 50 ; spec_i < speclen ; spec_i++)
	{
		if (spec_sum[spec_i]/FRAME_DETECT>0.07 && sqrt(std[spec_i]/FRAME_DETECT)/(spec_sum[spec_i]/FRAME_DETECT+0.0000000001)<0.1 ) count1++;
		//printf("%.4f\t%.4f\t%0.4f\n",spec_sum[spec_i]/16000,sqrt(std[spec_i]/16000),sqrt(std[spec_i]/16000)/(spec_sum[spec_i]/16000+0.0000000001));
	}
//    printf("稳定干扰音频段数:%d\t",count1);


	int count2=0; //能量聚集，但不检测方差
	for (int spec_i = 0 ; spec_i < speclen ; spec_i++)
	{
		if (spec_sum[spec_i]/FRAME_DETECT>0.5 ) count2++;
		//printf("%.4f\t%.4f\t%0.4f\n",spec_sum[spec_i]/16000,sqrt(std[spec_i]/16000),sqrt(std[spec_i]/16000)/(spec_sum[spec_i]/16000+0.0000000001));
	}

//    printf("能量集中频段数:%d\t",count2);

	destroy_spectrum (spec) ;

	return count1+count2;


} /* render_to_surface */

int
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
	//printf("filename:%s,totalframe:%lld,", render->sndfilepath,info.frames);
	int rr=render_to_surface (render, infile, info.samplerate, info.frames);
	

	sf_close (infile) ;

	return rr;
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
	render.height = 2000 ;

	render.filename = strrchr (render.sndfilepath, '/') ;
	render.filename = (render.filename != NULL) ? render.filename + 1 : render.sndfilepath ;

	int rr=render_sndfile (&render) ;

	if (rr!=0) 
	{
		printf("invalid:%d\n",rr );
		return 0;
	}else
	{
		printf("ok\n");
		return 0 ;
	}

	
} /* main */
