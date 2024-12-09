CREATE TABLE IF NOT EXISTS "Technology" (
	"tech"	text,
	"flag"	text,
	"sector"	text,
	"description"	text,
	"category"	text,
	"data_flags" text, 
	"reference" text,
	"additional_notes" text, sub_category, unlim_cap INTEGER, annual INTEGER, reserve INTEGER, curtail INTEGER, retire INTEGER, flex INTEGER, exchange INTEGER,

	FOREIGN KEY("reference") REFERENCES "references"(reference),
	PRIMARY KEY("tech"),
	FOREIGN KEY("flag") REFERENCES "TechnologyType"("label"),
	FOREIGN KEY("sector") REFERENCES "SectorLabel"("sector")
);
CREATE TABLE IF NOT EXISTS "Commodity" (
	"name"	text,
	"flag"	text,
	"description"	text,
	'data_flags' text, 
	"reference" text,
	"additional_notes" text,

	FOREIGN KEY("reference") REFERENCES "references"(reference),
	PRIMARY KEY("name"),
	FOREIGN KEY("flag") REFERENCES "CommodityType"("label")
);
CREATE TABLE IF NOT EXISTS "data_flags" (
	"data_flags" text,
	"description" text
	);
CREATE TABLE IF NOT EXISTS "TechOutputSplit" (
	"region"	TEXT,
	"period"	integer,
	"tech"	TEXT,
	"output_comm"	text,
	"min_proportion"	real,
	"notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("region","period","tech","output_comm", 'data_flags'),
	FOREIGN KEY("output_comm") REFERENCES "Commodity"("name"),
	FOREIGN KEY("period") REFERENCES "TimePeriod"("period"),
	FOREIGN KEY("tech") REFERENCES "Technology"("tech")
);
CREATE TABLE "TechOutputSplitAverage" (
	"region"	TEXT,
	"period"	integer,
	"tech"	TEXT,
	"output_comm"	text,
	"min_proportion"	real,
	"notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("region","period","tech","output_comm"),
	FOREIGN KEY("output_comm") REFERENCES "Commodity"("name"),
	FOREIGN KEY("period") REFERENCES "TimePeriod"("period"),
	FOREIGN KEY("tech") REFERENCES "Technology"("tech")
);
CREATE TABLE IF NOT EXISTS "TechInputSplit" (
	"region"	TEXT,
	"period"	integer,
	"input_comm"	text,
	"tech"	text,
	"min_proportion"	real,
	"notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("region","period","input_comm","tech",'data_flags'),
	FOREIGN KEY("tech") REFERENCES "Technology"("tech"),
	FOREIGN KEY("input_comm") REFERENCES "Commodity"("name"),
	FOREIGN KEY("period") REFERENCES "TimePeriod"("period")
);
CREATE TABLE IF NOT EXISTS "TechInputSplitAverage" (
	"region"	TEXT,
	"period"	integer,
	"input_comm"	text,
	"tech"	text,
	"min_proportion"	real,
	"notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("region","period","input_comm","tech",'data_flags'),
	FOREIGN KEY("input_comm") REFERENCES "Commodity"("name"),
	FOREIGN KEY("tech") REFERENCES "Technology"("tech"),
	FOREIGN KEY("period") REFERENCES "TimePeriod"("period")
);
CREATE TABLE IF NOT EXISTS "TimeSegmentFraction" (
	"season"	text,
	"tod"	text,
	"segfrac"	real CHECK("segfrac" >= 0 AND "segfrac" <= 1),
	"notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("season","tod"),
	FOREIGN KEY("season") REFERENCES "TimeSeason"("season"),
	FOREIGN KEY("tod") REFERENCES "TimeOfDay"("tod")
);
CREATE TABLE IF NOT EXISTS "PlanningReserveMargin" (
	"region"	text,
	"margin"	REAL,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY('region', 'data_flags'),
	FOREIGN KEY("region") REFERENCES "Region"
);
CREATE TABLE IF NOT EXISTS "RampDown" (
	"region"	text,
	`tech`	text,
	"rate" real,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("region", "tech", 'data_flags'),
	FOREIGN KEY("tech") REFERENCES "Technology"("tech")
);
CREATE TABLE IF NOT EXISTS "RampUp" (
	"region"	text,
	`tech`	text,
	"rate" real,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("region", "tech", 'data_flags'),
	FOREIGN KEY("tech") REFERENCES "Technology"("tech")
);
CREATE TABLE IF NOT EXISTS "MinCapacity" (
	"region"	text,
	"period"	integer,
	"tech"	text,
	"min_cap"	real,
	"units"	text,
	"notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("region","period","tech", 'data_flags'),
	FOREIGN KEY("tech") REFERENCES "Technology"("tech"),
	FOREIGN KEY("period") REFERENCES "TimePeriod"("period")
);
CREATE TABLE IF NOT EXISTS "MinActivity" (
	"region"	text,
	"period"	integer,
	"tech"	text,
	"min_act"	real,
	"units"	text,
	"notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("region","period","tech", 'data_flags'),
	FOREIGN KEY("tech") REFERENCES "Technology"("tech"),
	FOREIGN KEY("period") REFERENCES "TimePeriod"("period")
);
CREATE TABLE IF NOT EXISTS "MaxCapacity" (
	"region"	text,
	"period"	integer,
	"tech"	text,
	"max_cap"	real,
	"units"	text,
	"notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("region","period","tech", 'data_flags'),
	FOREIGN KEY("period") REFERENCES "TimePeriod"("period"),
	FOREIGN KEY("tech") REFERENCES "Technology"("tech")
);
CREATE TABLE IF NOT EXISTS "MaxActivity" (
	"region"	text,
	"period"	integer,
	"tech"	text,
	"max_act"	real,
	"units"	text,
	"notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("region","period","tech", 'data_flags'),
	FOREIGN KEY("period") REFERENCES "TimePeriod"("period"),
	FOREIGN KEY("tech") REFERENCES "Technology"("tech")
);
CREATE TABLE IF NOT EXISTS "MinAnnualCapacityFactor" (
	"region"	text,
	"period"	integer,
	"tech"	text,
	"output_comm" text,
	"factor"	real CHECK("factor" >= 0 AND "factor" <= 1),
	"notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text, source,

	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")

	PRIMARY KEY("region","period","tech","output_comm", 'data_flags'),
	FOREIGN KEY("period") REFERENCES "TimePeriod"("period"),
	FOREIGN KEY("tech") REFERENCES "Technology"("tech"),
	FOREIGN KEY("output_comm") REFERENCES "Commodity"("name")
);
CREATE TABLE IF NOT EXISTS "MaxAnnualCapacityFactor" (
	"region"	text,
	"period"	integer,
	"tech"	text,
	"output_comm" text,
	"factor"	real CHECK("factor" >= 0 AND "factor" <= 1),
	"notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text, source,

	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")

	PRIMARY KEY("region","period","tech","output_comm",'data_flags'),
	FOREIGN KEY("period") REFERENCES "TimePeriod"("period"),
	FOREIGN KEY("tech") REFERENCES "Technology"("tech"),
	FOREIGN KEY("output_comm") REFERENCES "Commodity"("name")
);
CREATE TABLE IF NOT EXISTS "LifetimeTech" (
	"region"	text,
	"tech"	text,
	"lifetime"	real,
	"notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("region","tech", 'data_flags'),
	FOREIGN KEY("tech") REFERENCES "Technology"("tech")
);
CREATE TABLE IF NOT EXISTS "LifetimeProcess" (
	"region"	text,
	"tech"	text,
	"vintage"	integer,
	"lifetime"	real,
	"notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("region","tech","vintage", 'data_flags'),
	FOREIGN KEY("vintage") REFERENCES "TimePeriod"("period"),
	FOREIGN KEY("tech") REFERENCES "Technology"("tech")
);
CREATE TABLE IF NOT EXISTS "LoanLifetimeTech" (
	"region"	text,
	"tech"	text,
	"lifetime"	real,
	"notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("region","tech", 'data_flags'),
	FOREIGN KEY("tech") REFERENCES "Technology"("tech")
);
CREATE TABLE IF NOT EXISTS "GrowthRateSeed" (
	"region"	text,
	"tech"	text,
	"seed"	real,
	"units"	text,
	"notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("region","tech", 'data_flags'),
	FOREIGN KEY("tech") REFERENCES "Technology"("tech")
);
CREATE TABLE IF NOT EXISTS "GrowthRateMax" (
	"region"	text,
	"tech"	text,
	"rate"	real,
	"notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("region","tech", 'data_flags'),
	FOREIGN KEY("tech") REFERENCES "Technology"("tech")
);
CREATE TABLE IF NOT EXISTS "ExistingCapacity" (
	"region"	text,
	"tech"	text,
	"vintage"	integer,
	"capacity"	real,
	"units"	text,
	"notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("region","tech","vintage", 'data_flags'),
	FOREIGN KEY("tech") REFERENCES "Technology"("tech"),
	FOREIGN KEY("vintage") REFERENCES "TimePeriod"("period")
);
CREATE TABLE IF NOT EXISTS "EmissionLimit" (
	"region"	text,
	"period"	integer,
	"emis_comm"	text,
	"value"	real,
	"units"	text,
	"notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("region","period","emis_comm", 'data_flags'),
	FOREIGN KEY("period") REFERENCES "TimePeriod"("period"),
	FOREIGN KEY("emis_comm") REFERENCES "Commodity"("name")
);
CREATE TABLE IF NOT EXISTS "EmissionActivity" (
	"region"	text,
	"emis_comm"	text,
	"input_comm"	text,
	"tech"	text,
	"vintage"	integer,
	"output_comm"	text,
	"activity"	real,
	"units"	text,
	"notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("region","emis_comm","input_comm","tech","vintage","output_comm", 'data_flags'),
	FOREIGN KEY("input_comm") REFERENCES "Commodity"("name"),
	FOREIGN KEY("tech") REFERENCES "Technology"("tech"),
	FOREIGN KEY("vintage") REFERENCES "TimePeriod"("period"),
	FOREIGN KEY("output_comm") REFERENCES "Commodity"("name"),
	FOREIGN KEY("emis_comm") REFERENCES "Commodity"("name")
);
CREATE TABLE IF NOT EXISTS "Efficiency" (
	"region"	text,
	"input_comm"	text,
	"tech"	text,
	"vintage"	integer,
	"output_comm"	text,
	"efficiency"	real CHECK("efficiency" > 0),
	"notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("region","input_comm","tech","vintage","output_comm", 'data_flags'),
	FOREIGN KEY("output_comm") REFERENCES "Commodity"("name"),
	FOREIGN KEY("tech") REFERENCES "Technology"("tech"),
	FOREIGN KEY("vintage") REFERENCES "TimePeriod"("period"),
	FOREIGN KEY("input_comm") REFERENCES "Commodity"("name")
);
CREATE TABLE IF NOT EXISTS "Demand" (
	"region"	text,
	"period"	integer,
	"commodity"	text,
	"demand"	real,
	"units"	text,
	"notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("region","period","commodity", 'data_flags'),
	FOREIGN KEY("period") REFERENCES "TimePeriod"("period"),
	FOREIGN KEY("commodity") REFERENCES "Commodity"("name")
);
CREATE TABLE IF NOT EXISTS "CostVariable" (
	"region"	text NOT NULL,
	"period"	integer NOT NULL,
	"tech"	text NOT NULL,
	"vintage"	integer NOT NULL,
	"cost"	real,
	"units"	text,
	"notes"	text,
	"data_cost_variable" REAL,
	"data_cost_year" INTEGER,
	"data_curr" TEXT,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,

	FOREIGN KEY("data_curr") REFERENCES "currencies"("curr_label"),	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("region","period","tech","vintage", 'data_flags'),
	FOREIGN KEY("tech") REFERENCES "Technology"("tech"),
	FOREIGN KEY("vintage") REFERENCES "TimePeriod"("period"),
	FOREIGN KEY("period") REFERENCES "TimePeriod"("period")
);
CREATE TABLE IF NOT EXISTS "CostInvest" (
	"region"	text,
	"tech"	text,
	"vintage"	integer,
	"cost"	real,
	"units"	text,
	"notes"	text,
	"data_cost_invest" REAL,
	"data_cost_year" INTEGER,
	"data_curr" TEXT,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("data_curr") REFERENCES "currencies"("curr_label"),
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("region","tech","vintage", 'data_flags'),
	FOREIGN KEY("tech") REFERENCES "Technology"("tech"),
	FOREIGN KEY("vintage") REFERENCES "TimePeriod"("period")
);
CREATE TABLE IF NOT EXISTS "CostFixed" (
	"region"	text NOT NULL,
	"period"	integer NOT NULL,
	"tech"	text NOT NULL,
	"vintage"	integer NOT NULL,
	"cost"	real,
	"units"	text,
	"notes"	text,
	"data_cost_fixed" REAL,
	"data_cost_year" INTEGER,
	"data_curr" TEXT,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("data_curr") REFERENCES "currencies"("curr_label"),
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("region","period","tech","vintage", 'data_flags'),
	FOREIGN KEY("tech") REFERENCES "Technology"("tech"),
	FOREIGN KEY("vintage") REFERENCES "TimePeriod"("period"),
	FOREIGN KEY("period") REFERENCES "TimePeriod"("period")
);
CREATE TABLE IF NOT EXISTS "CapacityToActivity" (
	"region"	text,
	"tech"	text,
	"c2a"	real,
	"notes"	TEXT,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("region","tech",'data_flags'),
	FOREIGN KEY("tech") REFERENCES "Technology"("tech")
);
CREATE TABLE IF NOT EXISTS "CapacityFactorTech" (
	"region"	text,
	"season"	text,
	"tod"	text,
	"tech"	text,
	"factor"	real CHECK("factor" >= 0 AND "factor" <= 1),
	"cf_tech_notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("region","season","tod","tech", 'data_flags'),
	FOREIGN KEY("season") REFERENCES "TimeSeason"("season"),
	FOREIGN KEY("tod") REFERENCES "TimeOfDay"("tod"),
	FOREIGN KEY("tech") REFERENCES "Technology"("tech")
);
CREATE TABLE IF NOT EXISTS "CapacityFactorProcess" (
	"region"	text,
	"season"	text,
	"tod"	text,
	"tech"	text,
	"vintage"	integer,
	"factor"	real CHECK("factor" >= 0 AND "factor" <= 1),
	"notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("region","season","tod","tech","vintage", 'data_flags'),
	FOREIGN KEY("tech") REFERENCES "Technology"("tech"),
	FOREIGN KEY("season") REFERENCES "TimeSeason"("season"),
	FOREIGN KEY("tod") REFERENCES "TimeOfDay"("tod")
);
CREATE TABLE IF NOT EXISTS "CapacityCredit" (
	"region"	text,
	"period"	integer,
	"tech"	text,
	"vintage" integer,
	"credit"	real CHECK("credit" >= 0 AND "credit" <= 1),
	"notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	PRIMARY KEY("region","period","tech","vintage",'data_flags')
);
CREATE TABLE IF NOT EXISTS "MaxResource" (
	"region"	text,
	"tech"	text,
	"max_res"	real,
	"units"	text,
	"notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	FOREIGN KEY("tech") REFERENCES "Technology"("tech"),
	PRIMARY KEY("region","tech", 'data_flags')
);
CREATE TABLE IF NOT EXISTS "LinkedTech" (
	"primary_region"	text,
	"primary_tech"	text,
	"emis_comm" text, 
 	"driven_tech"	text,
	"notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	FOREIGN KEY("primary_tech") REFERENCES "Technology"("tech"),
	FOREIGN KEY("driven_tech") REFERENCES "Technology"("tech"),
	FOREIGN KEY("emis_comm") REFERENCES "Commodity"("name"),
	PRIMARY KEY("primary_region","primary_tech", "emis_comm", 'data_flags')
);
CREATE TABLE IF NOT EXISTS "MaxSeasonalActivity" (

	"region"	text,

	"period"	integer,

	"season"	text,

	"tech"	text,

	"max_act"	real,

	"units"	text,

	"notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	FOREIGN KEY("period") REFERENCES "TimePeriod"("period"),

	FOREIGN KEY("season") REFERENCES "TimeSeason"("season"),

	FOREIGN KEY("tech") REFERENCES "Technology"("tech"),

	PRIMARY KEY("region","period","season","tech", 'data_flags') 

);
CREATE TABLE IF NOT EXISTS "MinSeasonalActivity" (

	"region"	text,

	"period"	integer,

	"season"	text,

	"tech"	text,

	"min_act"	real,

	"units"	text,

	"notes"	text,

	"reference" text,
	"data_year" integer,
	"data_flags" text,
	"dq_est" integer,
	"dq_rel" integer,
	"dq_comp" integer,
	"dq_time" integer,
	"dq_geog" integer,
	"dq_tech" integer,
	"additional_notes" text,
	
	FOREIGN KEY("reference") REFERENCES "references"("reference"),
	FOREIGN KEY("dq_est") REFERENCES "dq_estimate"("data_quality_estimated"),
	FOREIGN KEY("dq_rel") REFERENCES "dq_estimate"("data_quality_reliability"),
	FOREIGN KEY("dq_comp") REFERENCES "dq_estimate"("data_quality_completeness"),
	FOREIGN KEY("dq_time") REFERENCES "dq_estimate"("data_quality_time_related"),
	FOREIGN KEY("dq_geog") REFERENCES "dq_estimate"("data_quality_geography"),
	FOREIGN KEY("dq_tech") REFERENCES "dq_estimate"("data_quality_technology")
	FOREIGN KEY("period") REFERENCES "TimePeriod"("period"),

	FOREIGN KEY("tech") REFERENCES "Technology"("tech"),

	FOREIGN KEY("season") REFERENCES "TimeSeason"("season"),

	PRIMARY KEY("region","period","season","tech",'data_flags')

);
CREATE TABLE IF NOT EXISTS "references" (

	"reference" text,

	CONSTRAINT references_PK PRIMARY KEY ("reference")
);
CREATE TABLE IF NOT EXISTS "CommodityType" (
"label" TEXT,
  "description" TEXT,
  "reference" REAL,
  "additional_notes" REAL
);
CREATE TABLE IF NOT EXISTS "currencies" (
"curr_label" TEXT,
  "currency_description" TEXT,
  "reference" REAL,
  "additional_notes" REAL
);
CREATE TABLE IF NOT EXISTS "dq_estimate" (
"data_quality_estimated" INTEGER,
  "dq_est_description" REAL,
  "reference" REAL,
  "additional_notes" REAL
);
CREATE TABLE IF NOT EXISTS "dq_reliability" (
"data_quality_reliability" INTEGER,
  "dq_rel_description" REAL,
  "reference" REAL,
  "additional_notes" REAL
);
CREATE TABLE IF NOT EXISTS "dq_completeness" (
"data_quality_completeness" INTEGER,
  "dq_comp_description" REAL,
  "reference" REAL,
  "additional_notes" REAL
);
CREATE TABLE IF NOT EXISTS "dq_time" (
"data_quality_time_related" INTEGER,
  "dq_time_description" REAL,
  "reference" REAL,
  "additional_notes" REAL
);
CREATE TABLE IF NOT EXISTS "dq_geography" (
"data_quality_geography" INTEGER,
  "dq_geog_description" REAL,
  "reference" REAL,
  "additional_notes" REAL
);
CREATE TABLE IF NOT EXISTS "dq_technology" (
"data_quality_technology" INTEGER,
  "dq_tech_description" REAL,
  "reference" REAL,
  "additional_notes" REAL
);
CREATE TABLE IF NOT EXISTS "Region" (
"region" TEXT,
  "region_note" TEXT,
  "reference" REAL,
  "additional_notes" REAL
);
CREATE TABLE IF NOT EXISTS "SectorLabel" (
"sector" TEXT,
  "reference" REAL,
  "additional_notes" REAL
);
CREATE TABLE IF NOT EXISTS "TechnologyType" (
"label" TEXT,
  "description" TEXT,
  "reference" REAL,
  "additional_notes" REAL
);
CREATE TABLE IF NOT EXISTS "TimePeriodType" (
"label" TEXT,
  "description" TEXT,
  "reference" REAL,
  "additional_notes" REAL
);
CREATE TABLE IF NOT EXISTS "TimePeriod" (
"period" INTEGER,
  "flag" TEXT,
  "reference" REAL,
  "additional_notes" REAL
, sequence);
CREATE TABLE IF NOT EXISTS "TimeSeason" (
"season" TEXT,
  "reference" REAL,
  "additional_notes" REAL
, sequence);
CREATE TABLE IF NOT EXISTS "TimeOfDay" (
"tod" TEXT,
  "reference" REAL,
  "additional_notes" REAL
, sequence);
CREATE TABLE IF NOT EXISTS "StorageDuration" (
"region" TEXT,
  "tech" TEXT,
  "duration" INTEGER,
  "notes" TEXT,
  "reference" REAL,
  "data_year" REAL,
  "data_flags" REAL,
  "dq_est" REAL,
  "dq_rel" REAL,
  "dq_comp" REAL,
  "dq_time" REAL,
  "dq_geog" REAL,
  "dq_tech" REAL,
  "additional_notes" REAL
);
CREATE TABLE IF NOT EXISTS "DemandSpecificDistribution" (
"region" TEXT,
  "season" TEXT,
  "tod" TEXT,
  "demand_name" TEXT,
  "dsd" REAL,
  "notes" TEXT,
  "reference" TEXT,
  "data_year" INTEGER,
  "data_flags" TEXT,
  "dq_est" TEXT,
  "dq_rel" INTEGER,
  "dq_comp" INTEGER,
  "dq_time" INTEGER,
  "dq_geog" INTEGER,
  "dq_tech" INTEGER,
  "additional_notes" TEXT
);
CREATE TABLE CostEmission
(
    region    TEXT
        REFERENCES Region (region),
    period    INTEGER
        REFERENCES TimePeriod (period),
    emis_comm TEXT NOT NULL
        REFERENCES Commodity (name),
    cost      REAL NOT NULL,
    units     TEXT,
    notes     TEXT, reference, data_year, data_flags, dq_est, dq_rel, dq_comp, dq_time, dq_geog, dq_tech, additional_notes,
    PRIMARY KEY (region, period, emis_comm, 'data_flags')
);
CREATE TABLE LoanRate
(
    region  TEXT,
    tech    TEXT
        REFERENCES Technology (tech),
    vintage INTEGER
        REFERENCES TimePeriod (period),
	"data_flags" TEXT
    rate    REAL,
    notes   TEXT,
    PRIMARY KEY (region, tech, vintage, 'data_flags')
);
CREATE TABLE MaxActivityGroup
(
    region     TEXT,
    period     INTEGER
        REFERENCES TimePeriod (period),
    group_name TEXT
        REFERENCES TechGroup (group_name),
    max_act    REAL,
    units      TEXT,
    notes      TEXT, reference, data_year, data_flags, dq_est, dq_rel, dq_comp, dq_time, dq_geog, dq_tech, additional_notes,
    PRIMARY KEY (region, period, group_name, 'data_flags')
);
CREATE TABLE MaxActivityShare
(
    region         TEXT,
    period         INTEGER
        REFERENCES TimePeriod (period),
    tech           TEXT
        REFERENCES Technology (tech),
    group_name     TEXT
        REFERENCES TechGroup (group_name),
    max_proportion REAL,
    notes          TEXT, reference, data_year, data_flags, dq_est, dq_rel, dq_comp, dq_time, dq_geog, dq_tech, additional_notes,
    PRIMARY KEY (region, period, tech, group_name, 'data_flags')
);
CREATE TABLE MaxCapacityGroup
(
    region     TEXT,
    period     INTEGER
        REFERENCES TimePeriod (period),
    group_name TEXT
        REFERENCES TechGroup (group_name),
    max_cap    REAL,
    units      TEXT,
    notes      TEXT, reference, data_year, data_flags, dq_est, dq_rel, dq_comp, dq_time, dq_geog, dq_tech, additional_notes,
    PRIMARY KEY (region, period, group_name, 'data_flags')
);
CREATE TABLE MaxCapacityShare
(
    region         TEXT,
    period         INTEGER
        REFERENCES TimePeriod (period),
    tech           TEXT
        REFERENCES Technology (tech),
    group_name     TEXT
        REFERENCES TechGroup (group_name),
    max_proportion REAL,
    notes          TEXT, reference, data_year, data_flags, dq_est, dq_rel, dq_comp, dq_time, dq_geog, dq_tech, additional_notes,
    PRIMARY KEY (region, period, tech, group_name, 'data_flags')
);
CREATE TABLE MaxNewCapacity
(
    region  TEXT,
    period  INTEGER
        REFERENCES TimePeriod (period),
    tech    TEXT
        REFERENCES Technology (tech),
    max_cap REAL,
    units   TEXT,
    notes   TEXT, reference, data_year, data_flags, dq_est, dq_rel, dq_comp, dq_time, dq_geog, dq_tech, additional_notes,
    PRIMARY KEY (region, period, tech, 'data_flags')
);
CREATE TABLE MaxNewCapacityGroup
(
    region      TEXT,
    period      INTEGER
        REFERENCES TimePeriod (period),
    group_name  TEXT
        REFERENCES TechGroup (group_name),
    max_new_cap REAL,
    units       TEXT,
    notes       TEXT, reference, data_year, data_flags, dq_est, dq_rel, dq_comp, dq_time, dq_geog, dq_tech, additional_notes,
    PRIMARY KEY (region, period, group_name, 'data_flags')
);
CREATE TABLE MaxNewCapacityShare
(
    region         TEXT,
    period         INTEGER
        REFERENCES TimePeriod (period),
    tech           TEXT
        REFERENCES Technology (tech),
    group_name     TEXT
        REFERENCES TechGroup (group_name),
    max_proportion REAL,
    notes          TEXT, reference, data_year, data_flags, dq_est, dq_rel, dq_comp, dq_time, dq_geog, dq_tech, additional_notes,
    PRIMARY KEY (region, period, tech, group_name, 'data_flags')
);
CREATE TABLE MetaData
(
    element TEXT,
    value   INT,
    notes   TEXT,
    PRIMARY KEY (element)
);
CREATE TABLE MetaDataReal
(
    element TEXT,
    value   REAL,
    notes   TEXT,

    PRIMARY KEY (element)
);
CREATE TABLE MinActivityGroup
(
    region     TEXT,
    period     INTEGER
        REFERENCES TimePeriod (period),
    group_name TEXT
        REFERENCES TechGroup (group_name),
    min_act    REAL,
    units      TEXT,
    notes      TEXT, reference, data_year, data_flags, dq_est, dq_rel, dq_comp, dq_time, dq_geog, dq_tech, additional_notes,
    PRIMARY KEY (region, period, group_name,'data_flags')
);
CREATE TABLE MinActivityShare
(
    region         TEXT,
    period         INTEGER
        REFERENCES TimePeriod (period),
    tech           TEXT
        REFERENCES Technology (tech),
    group_name     TEXT
        REFERENCES TechGroup (group_name),
    min_proportion REAL,
    notes          TEXT, reference, data_year, data_flags, dq_est, dq_rel, dq_comp, dq_time, dq_geog, dq_tech, additional_notes,
    PRIMARY KEY (region, period, tech, group_name, 'data_flags')
);
CREATE TABLE MinCapacityGroup
(
    region     TEXT,
    period     INTEGER
        REFERENCES TimePeriod (period),
    group_name TEXT
        REFERENCES TechGroup (group_name),
    min_cap    REAL,
    units      TEXT,
    notes      TEXT, reference, data_year, data_flags, dq_est, dq_rel, dq_comp, dq_time, dq_geog, dq_tech, additional_notes,
    PRIMARY KEY (region, period, group_name, 'data_flags')
);
CREATE TABLE MinCapacityShare
(
    region         TEXT,
    period         INTEGER
        REFERENCES TimePeriod (period),
    tech           TEXT
        REFERENCES Technology (tech),
    group_name     TEXT
        REFERENCES TechGroup (group_name),
    min_proportion REAL,
    notes          TEXT, reference, data_year, data_flags, dq_est, dq_rel, dq_comp, dq_time, dq_geog, dq_tech, additional_notes,
    PRIMARY KEY (region, period, tech, group_name, 'data_flags')
);
CREATE TABLE MinNewCapacity
(
    region  TEXT,
    period  INTEGER
        REFERENCES TimePeriod (period),
    tech    TEXT
        REFERENCES Technology (tech),
    min_cap REAL,
    units   TEXT,
    notes   TEXT, reference, data_year, data_flags, dq_est, dq_rel, dq_comp, dq_time, dq_geog, dq_tech, additional_notes,
    PRIMARY KEY (region, period, tech, 'data_flags')
);
CREATE TABLE MinNewCapacityGroup
(
    region      TEXT,
    period      INTEGER
        REFERENCES TimePeriod (period),
    group_name  TEXT
        REFERENCES TechGroup (group_name),
    min_new_cap REAL,
    units       TEXT,
    notes       TEXT, reference, data_year, data_flags, dq_est, dq_rel, dq_comp, dq_time, dq_geog, dq_tech, additional_notes,
    PRIMARY KEY (region, period, group_name, 'data_flags')
);
CREATE TABLE MinNewCapacityShare
(
    region         TEXT,
    period         INTEGER
        REFERENCES TimePeriod (period),
    tech           TEXT
        REFERENCES Technology (tech),
    group_name     TEXT
        REFERENCES TechGroup (group_name),
    max_proportion REAL,
    notes          TEXT, reference, data_year, data_flags, dq_est, dq_rel, dq_comp, dq_time, dq_geog, dq_tech, additional_notes,
    PRIMARY KEY (region, period, tech, group_name, 'data_flags')
);
CREATE TABLE OutputBuiltCapacity
(
    scenario TEXT,
    region   TEXT,
    sector   TEXT
        REFERENCES SectorLabel (sector),
    tech     TEXT
        REFERENCES Technology (tech),
    vintage  INTEGER
        REFERENCES TimePeriod (period),
    capacity REAL,
    PRIMARY KEY (region, scenario, tech, vintage)
);
CREATE TABLE OutputCost
(
    scenario TEXT,
    region   TEXT,
    period   INTEGER,
    tech     TEXT,
    vintage  INTEGER,
    d_invest REAL,
    d_fixed  REAL,
    d_var    REAL,
    d_emiss  REAL,
    invest   REAL,
    fixed    REAL,
    var      REAL,
    emiss    REAL,
    PRIMARY KEY (scenario, region, period, tech, vintage),
    FOREIGN KEY (vintage) REFERENCES TimePeriod (period),
    FOREIGN KEY (tech) REFERENCES Technology (tech)
);
CREATE TABLE OutputCurtailment
(
    scenario    TEXT,
    region      TEXT,
    sector      TEXT,
    period      INTEGER
        REFERENCES TimePeriod (period),
    season      TEXT
        REFERENCES TimePeriod (period),
    tod         TEXT
        REFERENCES TimeOfDay (tod),
    input_comm  TEXT
        REFERENCES Commodity (name),
    tech        TEXT
        REFERENCES Technology (tech),
    vintage     INTEGER
        REFERENCES TimePeriod (period),
    output_comm TEXT
        REFERENCES Commodity (name),
    curtailment REAL,
    PRIMARY KEY (region, scenario, period, season, tod, input_comm, tech, vintage, output_comm)
);
CREATE TABLE OutputDualVariable
(
    scenario        TEXT,
    constraint_name TEXT,
    dual            REAL,
    PRIMARY KEY (constraint_name, scenario)
);
CREATE TABLE OutputEmission
(
    scenario  TEXT,
    region    TEXT,
    sector    TEXT
        REFERENCES SectorLabel (sector),
    period    INTEGER
        REFERENCES TimePeriod (period),
    emis_comm TEXT
        REFERENCES Commodity (name),
    tech      TEXT
        REFERENCES Technology (tech),
    vintage   INTEGER
        REFERENCES TimePeriod (period),
    emission  REAL,
    PRIMARY KEY (region, scenario, period, emis_comm, tech, vintage)
);
CREATE TABLE OutputFlowIn
(
    scenario    TEXT,
    region      TEXT,
    sector      TEXT
        REFERENCES SectorLabel (sector),
    period      INTEGER
        REFERENCES TimePeriod (period),
    season      TEXT
        REFERENCES TimeSeason (season),
    tod         TEXT
        REFERENCES TimeOfDay (tod),
    input_comm  TEXT
        REFERENCES Commodity (name),
    tech        TEXT
        REFERENCES Technology (tech),
    vintage     INTEGER
        REFERENCES TimePeriod (period),
    output_comm TEXT
        REFERENCES Commodity (name),
    flow        REAL,
    PRIMARY KEY (region, scenario, period, season, tod, input_comm, tech, vintage, output_comm)
);
CREATE TABLE OutputFlowOut
(
    scenario    TEXT,
    region      TEXT,
    sector      TEXT
        REFERENCES SectorLabel (sector),
    period      INTEGER
        REFERENCES TimePeriod (period),
    season      TEXT
        REFERENCES TimePeriod (period),
    tod         TEXT
        REFERENCES TimeOfDay (tod),
    input_comm  TEXT
        REFERENCES Commodity (name),
    tech        TEXT
        REFERENCES Technology (tech),
    vintage     INTEGER
        REFERENCES TimePeriod (period),
    output_comm TEXT
        REFERENCES Commodity (name),
    flow        REAL,
    PRIMARY KEY (region, scenario, period, season, tod, input_comm, tech, vintage, output_comm)
);
CREATE TABLE OutputNetCapacity
(
    scenario TEXT,
    region   TEXT,
    sector   TEXT
        REFERENCES SectorLabel (sector),
    period   INTEGER
        REFERENCES TimePeriod (period),
    tech     TEXT
        REFERENCES Technology (tech),
    vintage  INTEGER
        REFERENCES TimePeriod (period),
    capacity REAL,
    PRIMARY KEY (region, scenario, period, tech, vintage)
);
CREATE TABLE OutputObjective
(
    scenario          TEXT,
    objective_name    TEXT,
    total_system_cost REAL
);
CREATE TABLE OutputRetiredCapacity
(
    scenario TEXT,
    region   TEXT,
    sector   TEXT
        REFERENCES SectorLabel (sector),
    period   INTEGER
        REFERENCES TimePeriod (period),
    tech     TEXT
        REFERENCES Technology (tech),
    vintage  INTEGER
        REFERENCES TimePeriod (period),
    capacity REAL,
    PRIMARY KEY (region, scenario, period, tech, vintage)
);
CREATE TABLE RPSRequirement
(
    region      TEXT    NOT NULL
        REFERENCES Region (region),
    period      INTEGER NOT NULL
        REFERENCES TimePeriod (period),
    tech_group  TEXT    NOT NULL
        REFERENCES TechGroup (group_name),
    requirement REAL    NOT NULL,
    notes       TEXT
);
CREATE TABLE StorageInit
(
    tech  TEXT
        PRIMARY KEY,
    value REAL,
    notes TEXT
, reference, data_year, data_flags, dq_est, dq_rel, dq_comp, dq_time, dq_geog, dq_tech, additional_notes);
CREATE TABLE TechGroup
(
    group_name TEXT
        PRIMARY KEY,
    notes      TEXT
);
CREATE TABLE TechGroupMember
(
    group_name TEXT
        REFERENCES TechGroup (group_name),
    tech       TEXT
        REFERENCES Technology (tech),
    PRIMARY KEY (group_name, tech)
);
